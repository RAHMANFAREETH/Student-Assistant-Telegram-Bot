"""V12 task authorization, privacy, CRUD, input validation and route tests."""
from __future__ import annotations
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from TEST_SUPER_MINIAPP_V120 import FakeApp, module
import super_miniapp_v120_tasks as tasks

ID1='e58d6d63-78a9-49a9-b7e7-9f7c36dd976e'
ID2='f58d6d63-78a9-49a9-b7e7-9f7c36dd976f'

class FakeQuery:
 def __init__(self,db,action='select',value=None):self.db=db;self.action=action;self.value=value;self.filters={};self.max=1000
 def select(self,*args,**kwargs):self.action='select';return self
 def eq(self,key,value):self.filters[key]=value;return self
 def order(self,*args,**kwargs):return self
 def limit(self,max_rows):self.max=max_rows;return self
 def insert(self,value):self.action='insert';self.value=value;return self
 def update(self,value):self.action='update';self.value=value;return self
 def delete(self):self.action='delete';return self
 def execute(self):
  self.db.queries.append((self.action,dict(self.filters)))
  def matches(row):return all(row.get(k)==v for k,v in self.filters.items())
  if self.action=='insert':
   row=dict(self.value)
   if any(r['user_id']==row['user_id'] and r['id']==row['id'] for r in self.db.rows):raise Exception('duplicate')
   self.db.rows.append(row);return SimpleNamespace(data=[row])
  found=[r for r in self.db.rows if matches(r)]
  if self.action=='select':return SimpleNamespace(data=[dict(r) for r in found[:self.max]])
  if self.action=='update':
   for row in found:row.update(self.value)
   return SimpleNamespace(data=[dict(r) for r in found])
  if self.action=='delete':
   for r in found:self.db.rows.remove(r)
   return SimpleNamespace(data=[dict(r) for r in found])
  raise AssertionError('unsupported action')

class FakeDB:
 def __init__(self):self.rows=[];self.queries=[]
 def table(self,name):
  assert name=='v120_quick_tasks'
  return FakeQuery(self)

class TestTaskStore(unittest.TestCase):
 def setUp(self):self.db=FakeDB()
 def test_create_and_list(self):
  item,created=tasks.create_task(44,{'id':ID1,'text':'  Read chapter 1  '},self.db)
  self.assertTrue(created);self.assertEqual(item['text'],'Read chapter 1')
  self.assertEqual(tasks.list_tasks(44,self.db),[item]);self.assertEqual(tasks.list_tasks(55,self.db),[])
 def test_duplicate_create_is_idempotent_and_does_not_overwrite(self):
  tasks.create_task(44,{'id':ID1,'text':'Original'},self.db)
  item,created=tasks.create_task(44,{'id':ID1,'text':'New text'},self.db)
  self.assertFalse(created);self.assertEqual(item['text'],'Original');self.assertEqual(len(self.db.rows),1)
 def test_two_users_same_id_do_not_leak(self):
  tasks.create_task(44,{'id':ID1,'text':'One'},self.db)
  tasks.create_task(55,{'id':ID1,'text':'Two'},self.db)
  self.assertEqual(tasks.list_tasks(44,self.db)[0]['text'],'One')
  self.assertEqual(tasks.list_tasks(55,self.db)[0]['text'],'Two')
 def test_update_only_signed_users_row(self):
  tasks.create_task(44,{'id':ID1,'text':'Mine'},self.db)
  self.assertIsNone(tasks.update_task(55,ID1,{'done':True},self.db))
  self.assertFalse(tasks.list_tasks(44,self.db)[0]['done'])
  self.assertTrue(tasks.update_task(44,ID1,{'done':True},self.db)['done'])
 def test_delete_only_owner_row(self):
  tasks.create_task(44,{'id':ID1,'text':'Mine'},self.db)
  tasks.delete_task(55,ID1,self.db);self.assertEqual(len(self.db.rows),1)
  tasks.delete_task(44,ID1,self.db);self.assertEqual(len(self.db.rows),0)
 def test_update_and_delete_queries_have_user_id(self):
  tasks.create_task(44,{'id':ID1,'text':'Mine'},self.db)
  self.db.queries.clear();tasks.update_task(44,ID1,{'done':True},self.db);tasks.delete_task(44,ID1,self.db)
  self.assertTrue(all(q[1].get('user_id')==44 for q in self.db.queries))
 def test_rejects_invalid_user_and_payload(self):
  for uid in [-1,True,'44',0]:
   with self.subTest(uid=uid),self.assertRaises(tasks.TaskInputError):tasks.list_tasks(uid,self.db)
  for body in [{}, {'id':ID1,'text':''}, {'id':ID1,'text':'a'*161}, {'id':ID1,'text':'ok','user_id':99}, {'id':'x','text':'ok'},{'id':ID1,'text':'ok','done':'true'}]:
   with self.subTest(body=body),self.assertRaises(tasks.TaskInputError):tasks.create_task(44,body,self.db)
 def test_limit_100(self):
  for _ in range(100):self.db.rows.append({'user_id':44,'id':str(uuid4()),'title':'x','done':False})
  with self.assertRaises(tasks.TaskLimitError):tasks.create_task(44,{'id':ID1,'text':'one more'},self.db)
 def test_input_rejects_non_boolean(self):
  with self.assertRaises(tasks.TaskInputError):tasks.update_task(44,ID1,{'done':1},self.db)
  with self.assertRaises(tasks.TaskInputError):tasks.update_task(44,ID1,{'done':False,'title':'unsafe'},self.db)

class TestTaskRoutes(unittest.TestCase):
 def setUp(self):
  self.app=FakeApp()
  module.register_super_miniapp(self.app)
  self.app.logger=SimpleNamespace(warning=lambda *args:None)
 def call(self,method='GET',path='collection',uid=44,body=None,flag='true'):
  fake_request=SimpleNamespace(headers={'X-Telegram-Init-Data':'signed'},method=method,content_length=100,get_json=lambda silent=True:body)
  view=self.app.view_functions['v120_super_tasks' if path=='collection' else 'v120_super_task_item']
  with patch.dict(os.environ,{'SUPER_MINIAPP_V120_ENABLED':flag}),patch.object(module,'request',fake_request),patch.object(module,'jsonify',side_effect=lambda obj:obj),patch.object(module,'verify_super_session',side_effect=(PermissionError('blocked') if uid=='blocked' else ValueError('bad') if uid is None else None),return_value=uid):
   if path=='collection':return view()
   return view(ID1)
 def test_unauthenticated_never_reads_database(self):
  with patch.object(tasks,'list_tasks') as db:
   response=self.call(uid=None);self.assertEqual(response[1],401);db.assert_not_called()
 def test_underage_never_reads_database(self):
  with patch.object(tasks,'list_tasks') as db:
   response=self.call(uid='blocked');self.assertEqual(response[1],403);db.assert_not_called()
 def test_feature_off_rejects_before_db(self):
  with patch.object(module,'abort',side_effect=RuntimeError('HTTP 404')):
   with self.assertRaisesRegex(RuntimeError,'404'):self.call(flag='false')
 def test_invalid_input_rejected(self):
  self.assertEqual(self.call(method='POST',body={})[1],400)
 def test_signed_get_does_not_accept_client_user_id(self):
  with patch.object(tasks,'list_tasks',return_value=[{'id':ID1,'text':'Own','done':False}]) as fn:
   result=self.call()
  self.assertTrue(result['ok']);fn.assert_called_once_with(44)
 def test_signed_write_uses_verified_user(self):
  with patch.object(tasks,'create_task',return_value=({'id':ID1,'text':'Own','done':False},True)) as fn:
   result=self.call(method='POST',body={'id':ID1,'text':'Own'})
  self.assertEqual(result[1],201);fn.assert_called_once_with(44,{'id':ID1,'text':'Own'})
 def test_secret_db_errors_hidden(self):
  with patch.object(tasks,'list_tasks',side_effect=RuntimeError('DB_SERVICE_ROLE_SECRET=ABC')):
   result=self.call()
  self.assertEqual(result[1],503);self.assertNotIn('ABC',repr(result))

if __name__=='__main__':unittest.main()
