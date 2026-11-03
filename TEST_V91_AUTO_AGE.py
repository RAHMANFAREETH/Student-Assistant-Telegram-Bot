import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import age_verification_v91 as age
from INSTALL_V91_AUTO_AGE import edited

SDK = 'b4c6a3ea-227a-4a66-80cc-b7fa144342a4'
SESSION = '5c596d3c-9f56-4f83-97af-3452c1caafcb'
NOW = datetime(2026,10,30,6,0,0,tzinfo=timezone.utc)

class Query:
    def __init__(self,store,table):
        self.store=store;self.table=table;self.filters={};self.action='read';self.data=None
    def select(self,*args,**kwargs):return self
    def eq(self,k,v):self.filters[k]=v;return self
    def limit(self,n):return self
    def upsert(self,data,on_conflict=None):self.action='upsert';self.data=data;return self
    def update(self,data):self.action='update';self.data=data;return self
    def execute(self):
        from types import SimpleNamespace
        if self.action=='upsert':
            self.store.setdefault(self.table,{})[self.data['user_id']] = dict(self.data)
            return SimpleNamespace(data=[self.data])
        if self.action=='update':
            for uid,row in self.store.get(self.table,{}).items():
                if all(row.get(k)==v for k,v in self.filters.items()):row.update(self.data)
            return SimpleNamespace(data=[])
        rows=[dict(row) for row in self.store.get(self.table,{}).values() if all(row.get(k)==v for k,v in self.filters.items())]
        return SimpleNamespace(data=rows)
class DB:
    def __init__(self):self.store={}
    def table(self,t):return Query(self.store,t)

class Response:
    def __init__(self, obj):self.obj=obj
    def raise_for_status(self):pass
    def json(self):return self.obj

class FakeHttp:
    def __init__(self):self.posts=[];self.gets=[];self.payload=None;self.status='PENDING'
    def post(self,url,**kwargs):
        self.posts.append((url,kwargs));self.payload=kwargs['json'];
        return Response({'id':SESSION,'expires_at':(NOW+timedelta(minutes=15)).isoformat(),'status':'PENDING'})
    def get(self,url,**kwargs):
        self.gets.append((url,kwargs));return Response({
            'id':SESSION,'reference_id':self.payload['reference_id'],
            'type':'OVER','age':18,'status':self.status})

class AgeTests(unittest.TestCase):
    def setUp(self):
        self.db=DB();self.http=FakeHttp()
        self.config=patch.object(age,'_config',return_value=('SECRET_KEY',SDK,'https://example.onrender.com'))
        self.config.start()
    def tearDown(self):self.config.stop()
    def start(self):return age.start(123,db=self.db,http=self.http,now=NOW)
    def poll(self):return age.status(123,db=self.db,http=self.http,now=NOW+timedelta(minutes=1))
    def test_create_session_18_and_safe_reference(self):
        link=self.start();self.assertTrue(link.startswith('https://age.yoti.com?'))
        payload=self.http.posts[0][1]['json']
        self.assertEqual(payload['type'],'OVER')
        self.assertEqual(payload['doc_scan']['threshold'],18)
        self.assertEqual(payload['digital_id']['threshold'],18)
        self.assertNotIn('123',payload['reference_id'])
        self.assertNotIn('123',link)
        self.assertEqual(self.db.store['study_age_sessions'][123]['daily_count'],1)
    def test_pending_no_access(self):
        self.start();self.assertEqual(self.poll(),'pending')
        self.assertNotIn('study_verified_adults',self.db.store)
    def test_verified_api_result_only(self):
        self.start();self.http.status='COMPLETE';self.assertEqual(self.poll(),'verified')
        record=self.db.store['study_verified_adults'][123]
        self.assertEqual(record['verification_method'],'trusted_provider')
        self.assertEqual(record['status'],'verified')
        self.assertGreater(age._parse_dt(record['valid_until']),NOW)
    def test_failed_result_does_not_grant(self):
        self.start();self.http.status='FAIL';self.assertEqual(self.poll(),'not_verified')
        self.assertNotIn('study_verified_adults',self.db.store)
    def test_mismatched_reference_never_granted(self):
        self.start();self.http.payload['reference_id']='tampered'
        with self.assertRaises(age.AgeVerificationError):self.poll()
        self.assertNotIn('study_verified_adults',self.db.store)
    def test_mismatched_session_never_granted(self):
        self.start();self.db.store['study_age_sessions'][123]['session_id']=str(uuid4())
        with self.assertRaises(age.AgeVerificationError):self.poll()
    def test_expired_never_granted(self):
        self.start();res=age.status(123,db=self.db,http=self.http,now=NOW+timedelta(minutes=16))
        self.assertEqual(res,'expired');self.assertEqual(len(self.http.gets),0)
    def test_reused_session_no_extra_charge(self):
        one=self.start();two=self.start();self.assertEqual(one,two);self.assertEqual(len(self.http.posts),1)
    def test_revoked_refuses_new_verification(self):
        self.db.store['study_verified_adults']={123:{'user_id':123,'status':'revoked'}}
        with self.assertRaises(age.AgeVerificationError):self.start()
        self.assertEqual(self.poll(),'restricted')
    def test_invalid_age_and_type_do_not_grant(self):
        self.start();self.http.status='COMPLETE'
        for fake in [17,None,True]:
            def bad_get(url,**kwargs):
                return Response({'id':SESSION,'reference_id':self.http.payload['reference_id'],
                                 'type':'OVER','status':'COMPLETE','age':fake})
            with patch.object(self.http,'get',side_effect=bad_get):
                self.assertEqual(self.poll(),'unconfirmed')
        self.assertNotIn('study_verified_adults',self.db.store)
    def test_suspicious_provider_result_cannot_approve(self):
        self.start();self.http.status='COMPLETE'
        def bad(url,**kwargs):
            return Response({'id':SESSION,'reference_id':self.http.payload['reference_id'],'type':'AGE','age':25,'status':'COMPLETE'})
        with patch.object(self.http,'get',side_effect=bad):
            self.assertEqual(self.poll(),'unconfirmed')
        self.assertNotIn('study_verified_adults',self.db.store)
    def test_no_record(self):self.assertEqual(self.poll(),'not_started')
    def test_existing_valid_adult_does_not_start_new(self):
        self.db.store['study_verified_adults']={123:{'user_id':123,'status':'verified','verification_method':'trusted_provider','valid_until':(NOW+timedelta(days=5)).isoformat()}}
        self.assertIsNone(self.start());self.assertEqual(len(self.http.posts),0)
    def test_disabled_requires_configuration(self):
        self.config.stop()
        try:
            with patch.dict(os.environ, {'V91_AGE_VERIFY_ENABLED':'false'}):
                with self.assertRaises(age.AgeVerificationError):age.start(123,db=self.db,http=self.http,now=NOW)
        finally:self.config.start()
    def test_invalid_public_url_refused(self):
        self.config.stop()
        try:
            with patch.dict(os.environ, {'V91_AGE_VERIFY_ENABLED':'true','YOTI_AGE_API_KEY':'secret','YOTI_AGE_SDK_ID':SDK,'V8_PUBLIC_URL':'http://evil.test'}):
                with self.assertRaises(age.AgeVerificationError):age._config()
        finally:self.config.start()
    def test_integration_idempotent(self):
        s='''register_v8_miniapp(app)\n\n# V9.0 optional Academic Toolkit. Register before the older V8 state handlers.\n'''
        self.assertEqual(edited(s),edited(edited(s)))
        self.assertIn('register_v91_age_handlers(bot)',edited(s))
        self.assertIn('register_v91_age_return(app)',edited(s))
    def test_upstream_cannot_grant_with_callback(self):
        import inspect
        src=inspect.getsource(age.register_v91_age_return)
        self.assertNotIn('study_verified_adults',src)

from uuid import uuid4
if __name__=='__main__':unittest.main()
