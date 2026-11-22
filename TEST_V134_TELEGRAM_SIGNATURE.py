import hashlib
import hmac
import unittest
from urllib.parse import urlencode

from v8_miniapp import validate_init_data, MiniAppAuthError


class TelegramSignatureTests(unittest.TestCase):
    token = "123456:TEST_TOKEN_ONLY"
    now = 1730000000

    def signed_data(self, signature=None):
        data = {
            "auth_date": str(self.now),
            "user": '{"id":2468}',
        }

        if signature is not None:
            data["signature"] = signature

        check = "\n".join(
            f"{key}={data[key]}" for key in sorted(data)
        )

        secret = hmac.new(
            b"WebAppData",
            self.token.encode(),
            hashlib.sha256
        ).digest()

        data["hash"] = hmac.new(
            secret,
            check.encode(),
            hashlib.sha256
        ).hexdigest()

        return urlencode(data)

    def test_telegram_signature_is_included(self):
        raw = self.signed_data("test_signature")

        self.assertEqual(
            validate_init_data(raw, self.token, now=self.now),
            2468
        )

        with self.assertRaises(MiniAppAuthError):
            validate_init_data(
                raw.replace("test_signature", "tampered_signature"),
                self.token,
                now=self.now
            )

    def test_older_clients_without_signature(self):
        self.assertEqual(
            validate_init_data(
                self.signed_data(),
                self.token,
                now=self.now
            ),
            2468
        )


if __name__ == "__main__":
    unittest.main()