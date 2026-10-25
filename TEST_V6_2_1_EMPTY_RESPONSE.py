"""Offline regression tests for V6.2.1, including source-compatibility checks."""
from __future__ import annotations
import ast
from pathlib import Path
import tempfile
import unittest
import INSTALL_V6_2_1 as installer

class InstallerTests(unittest.TestCase):
    def _synthetic(self):
        return '''CF_MODEL = "@cf/qwen/qwen3-30b-a3b-fp8"\n
def _provider_call(model, messages, max_tokens):
    requests.post("url", json={"messages": messages, "max_tokens": max_tokens}, timeout=12)
    try:
        result = {}
        if isinstance(result, dict):
            output = result.get("response")
            if output is None:
                choices = result.get("choices") or []
                if choices:
                    output = choices[0].get("message", {}).get("content")
    except Exception:
        pass

def _check_safety(text):
    return True

# V6.0 aggregate Cloudflare monitoring (no prompt data)
_provider_call = wrap_cloudflare_provider(_provider_call)
# V6.2 passive Cloudflare health observation (never changes outputs)
_provider_call = observe_cloudflare_health(_provider_call)
'''

    def test_patch_is_idempotent_and_keeps_wrappers(self):
        new, changed = installer.patch_ai(self._synthetic())
        self.assertTrue(changed)
        self.assertIn('observe_cloudflare_health(_provider_call)', new)
        self.assertIn('wrap_cloudflare_provider(_provider_call)', new)
        self.assertEqual(installer.patch_ai(new), (new, False))
        ast.parse(new)

    def test_qwen_only_no_think_and_no_mutation(self):
        src, _ = installer.patch_ai(self._synthetic())
        # Extract helper AST only, without needing project deps.
        node = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == '_v621_generation_payload')
        module = ast.Module(body=[node], type_ignores=[])
        namespace = {'CF_MODEL':'@cf/qwen/qwen3-30b-a3b-fp8'}
        exec(compile(module, '<test>', 'exec'), namespace)
        fn = namespace['_v621_generation_payload']
        orig = [{'role':'system', 'content':'Be helpful'}, {'role':'user','content':'Photosynthesis in Tamil'}]
        generated = fn(namespace['CF_MODEL'], orig, 650)
        self.assertEqual(generated['messages'][-1]['content'], 'Photosynthesis in Tamil\n/no_think')
        self.assertEqual(orig[-1]['content'], 'Photosynthesis in Tamil')
        self.assertEqual(generated['max_tokens'], 650)
        guard = fn('@cf/meta/llama-guard-3-8b', orig, 64)
        self.assertIs(guard['messages'], orig)
        self.assertNotIn('/no_think', str(guard))

    def test_patch_rejects_wrong_source_without_edit(self):
        with self.assertRaises(ValueError):
            installer.patch_ai('def foo(): pass')
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / installer.NAME
            p.write_text('def foo(): pass',encoding='utf-8')
            with self.assertRaises(ValueError):
                installer.run(Path(td))
            self.assertEqual(p.read_text(), 'def foo(): pass')
            self.assertFalse(list(Path(td).glob('*.bak')))

    def test_windows_crlf_input(self):
        source = self._synthetic().replace('\n', '\r\n')
        patched, yes = installer.patch_ai(source)
        self.assertTrue(yes)
        self.assertIn('            if not isinstance(output, str) or not output.strip():\r\n', patched)
        self.assertNotIn('\r\r\n', patched)
        self.assertEqual(installer.patch_ai(patched), (patched, False))
        ast.parse(patched)

    def test_backup_and_second_install(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            p = folder / installer.NAME
            orig = self._synthetic()
            p.write_text(orig, encoding='utf-8')
            self.assertTrue(installer.run(folder))
            self.assertEqual((folder / (installer.NAME+'.before_v621.bak')).read_text(encoding='utf-8'), orig)
            self.assertFalse(installer.run(folder))

if __name__ == '__main__':
    unittest.main()
