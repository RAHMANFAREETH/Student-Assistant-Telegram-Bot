"""Isolated V12.0.2 tests; run under the existing bot's Flask environment."""
import base64
import os
import sys
import unittest
from unittest.mock import patch

try:
    import flask
except ImportError:
    flask = None

if flask:
    from flask import Flask
    import super_miniapp_v120_exports as ex

PNG=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL/nwAAAABJRU5ErkJggg==")


@unittest.skipUnless(flask is not None, "Flask is available in the user's bot environment")
class ExportRouteTests(unittest.TestCase):
    def setUp(self):
        self.flags=patch.dict(os.environ,{"SUPER_MINIAPP_V120_ENABLED":"true",
                                        "SUPER_MINIAPP_V120_PUBLIC_TOOLS":"true"})
        self.flags.start()
        self.app=Flask("v120_test_exports")
        ex.register_v120_exports(self.app)
        self.client=self.app.test_client()
        with ex._LOCK:
            ex._ITEMS.clear()
            ex._RATE.clear()

    def tearDown(self):
        self.flags.stop()

    def test_consent_required(self):
        res=self.client.post("/app/api/export",data=PNG,content_type="image/png")
        self.assertEqual(res.status_code,400)

    def test_image_export_and_native_download_headers(self):
        r=self.client.post("/app/api/export",data=PNG,content_type="image/png",
                           headers={"X-V120-Export-Intent":"1",
                                    "X-V120-Export-Name":"signature.png"})
        self.assertEqual(r.status_code,201,r.get_json())
        url=r.get_json()["path"]
        dl=self.client.get(url)
        self.assertEqual(dl.status_code,200)
        self.assertEqual(dl.data,PNG)
        self.assertIn("attachment",dl.headers["Content-Disposition"])
        self.assertIn("signature.png",dl.headers["Content-Disposition"])
        self.assertEqual(dl.headers["Access-Control-Allow-Origin"],"https://web.telegram.org")
        self.assertIn("no-store",dl.headers["Cache-Control"])

    def test_invalid_image_denied(self):
        r=self.client.post("/app/api/export",data=b"Not an image"*8,content_type="image/png",
                           headers={"X-V120-Export-Intent":"1"})
        self.assertEqual(r.status_code,400)

    def test_unsupported_type_denied(self):
        r=self.client.post("/app/api/export",data=b"<svg><script></script></svg>",
                           content_type="image/svg+xml",headers={"X-V120-Export-Intent":"1"})
        self.assertEqual(r.status_code,415)

    def test_disabled_by_flag(self):
        os.environ["SUPER_MINIAPP_V120_ENABLED"]="false"
        self.assertEqual(self.client.post("/app/api/export").status_code,404)

    def test_large_file_rejected(self):
        r=self.client.post("/app/api/export",data=b"a"*(ex._MAX_FILE+1),content_type="image/png",
                           headers={"X-V120-Export-Intent":"1"})
        self.assertEqual(r.status_code,413)

    def test_short_lived_url(self):
        r=self.client.post("/app/api/export",data=PNG,content_type="image/png",
                           headers={"X-V120-Export-Intent":"1"})
        url=r.get_json()["path"]
        with ex._LOCK:
            token=url.rsplit("/",1)[-1]
            expiry,data,mime,name=ex._ITEMS[token]
            ex._ITEMS[token]=(0,data,mime,name)
        self.assertEqual(self.client.get(url).status_code,404)

    def test_invalid_token_rejected(self):
        self.assertEqual(self.client.get("/app/exports/../../secret").status_code,404)


if __name__=="__main__":
    unittest.main()
