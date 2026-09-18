import sys
import unittest
import tempfile
import zipfile
import io
import ast
import base64
import importlib.util
import json
from unittest.mock import patch
from types import SimpleNamespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run import assign_splits, evidence_status, compare_runs, evaluate_rows, validate_config


class ExperimentsTest(unittest.TestCase):
    def test_full_runner_writes_paired_results_and_missing_data_status(self):
        import run
        from legalqa_baseline import generation, scoring
        class Generator:
            def __init__(self, *args, **kwargs):
                pass
            def generate(self, question, context, metadata, **kwargs):
                self.assert_no_reference = 'SECRET' not in str((question, context, metadata, kwargs))
                if not self.assert_no_reference:
                    raise AssertionError('reference leaked')
                return {'lead': 'lead', 'conclusion': 'end', 'context_truncated': False}
        def scorer(predictions, references):
            return {'per_sample': [{'meteor': .2, 'rouge': .3} for _ in predictions]}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'configs').mkdir()
            (root / 'adapter').mkdir()
            (root / 'adapter' / 'adapter_model.safetensors').write_bytes(b'test adapter identity')
            (root / 'configs' / 'production.json').write_text(json.dumps({
                'model_key': 'test', 'prompt_mode': 'v8_sft', 'enable_quality_retry': True}))
            (root / 'configs' / 'models.json').write_text(json.dumps({'test': {}}))
            (root / 'packages.json').write_text(json.dumps([{'id': '1', 'question': 'Q',
                'contexts': [{'text': 'law'}], 'reference_answer': 'SECRET'}]))
            config = {'packages': 'packages.json', 'top_k': 1, 'seed': 42,
                      'limit': None, 'models': ['base', 'adapter'], 'score_threshold': .5}
            (root / 'config.json').write_text(json.dumps(config))
            argv = ['run.py', '--config', str(root / 'config.json'), '--adapter-path', str(root / 'adapter'),
                    '--output', str(root / 'results')]
            with patch.object(run, 'ROOT', root), patch.object(sys, 'argv', argv), \
                 patch.object(generation, 'QwenGenerator', Generator), patch.object(scoring, 'score_text_pairs', scorer), \
                 patch.dict(sys.modules, {'torch': SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))}):
                run.main()
            manifest = json.loads((root / 'results' / 'manifest.json').read_text())
            self.assertEqual(manifest['status'], 'completed')
            self.assertEqual(manifest['splits'], {'1': 'unverified'})
            self.assertEqual(len(manifest['missing']), 3)
            comparisons = json.loads((root / 'results' / 'comparisons.json').read_text())
            self.assertEqual(comparisons['adapter_retrieved_minus_base_retrieved']['meteor']['mean_delta'], 0)

    def test_invalid_config_fails_before_loading_models(self):
        config = {'top_k': 1, 'seed': 42, 'limit': 20, 'models': ['base', 'adapter'], 'score_threshold': .5}
        validate_config(config)
        for key, bad in [('top_k', 0), ('seed', -1), ('limit', -1), ('models', ['base', 'base']), ('score_threshold', 2)]:
            with self.assertRaises(ValueError):
                validate_config({**config, key: bad})

    def test_kaggle_bundle_is_private_and_contains_both_modules(self):
        spec = importlib.util.spec_from_file_location('experiment_build', Path(__file__).with_name('kaggle.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            target = module.build(Path(__file__).with_name('config.json'), root / 'inputs' / 'example.json', Path(tmp) / 'build')
            import json
            metadata = json.loads((target / 'kernel' / 'kernel-metadata.json').read_text())
            self.assertEqual(metadata['is_private'], 'true')
            self.assertNotIn('production', metadata['id'])
            tree = ast.parse((target / 'kernel' / 'run_experiments.py').read_text(encoding='utf-8'))
            bundle = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                          and any(isinstance(t, ast.Name) and t.id == 'SOURCE_BUNDLE' for t in n.targets))
            with zipfile.ZipFile(io.BytesIO(base64.b64decode(bundle))) as archive:
                self.assertIn('legalQA_Task2/scripts/run_retrieval.py', archive.namelist())
                self.assertIn('legalQA_Task2/ChanTaooDe--main/src/b2_retrieval/retrieve.py', archive.namelist())
                self.assertIn('legalQA_Task2/experiments/run.py', archive.namelist())

    def test_context_expansion_preserves_all_covered_unit_ids(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
        from run_retrieval import context_item, strict_unit
        doc = {'context_id': '7', 'parse_status': 'matched', 'name': 'Law', 'link': '',
               'dieu': [{'dieu_id': '7_2', 'text': 'whole article', 'khoan': [
                   {'khoan_id': '7_2_1', 'text': 'one'}, {'khoan_id': '7_2_2', 'text': 'two'}]}]}
        item = context_item(doc, '7_2_1', .9, True)
        self.assertEqual(item['text'], 'whole article')
        self.assertTrue(evidence_status({'gold_unit_ids': ['7_2_2']}, [item]))
        with self.assertRaises(ValueError):
            strict_unit(doc, '7_99')

    def test_split_requires_actual_membership_and_rejects_leakage(self):
        rows = [{'id': '1', 'question': 'A?'}, {'id': '2', 'question': 'B?'}]
        self.assertEqual(assign_splits(rows, None), {'1': 'unverified', '2': 'unverified'})
        manifest = {'source': 'training export', 'train_ids': ['1'], 'heldout_ids': ['2']}
        self.assertEqual(assign_splits(rows, manifest)['2'], 'heldout')
        manifest['heldout_ids'] = ['1']
        with self.assertRaises(ValueError):
            assign_splits(rows, manifest)
        manifest['heldout_ids'] = ['2']
        rows[1]['question'] = '  a? '
        with self.assertRaises(ValueError):
            assign_splits(rows, manifest)

    def test_evidence_unknown_is_not_miss(self):
        self.assertIsNone(evidence_status({}, [{'unit_id': 'a'}]))
        self.assertFalse(evidence_status({'gold_unit_ids': ['a', 'b']}, [{'unit_id': 'a'}]))
        self.assertTrue(evidence_status({'gold_unit_ids': ['a', 'b']}, [{'covered_unit_ids': ['a', 'b']}]))
        self.assertIsNone(evidence_status({'gold_unit_ids': ['b']}, [{'unit_id': 'a'}, {'text': 'unannotated'}]))
        self.assertTrue(evidence_status({'gold_unit_ids': ['a']}, [{'unit_id': 'a'}, {'text': 'unannotated'}]))

    def test_pairing_uses_ids_not_position(self):
        a = [{'id': '1', 'meteor': .1}, {'id': '2', 'meteor': .9}]
        b = [{'id': '2', 'meteor': .8}, {'id': '1', 'meteor': .3}]
        self.assertAlmostEqual(compare_runs(a, b, 'meteor', 42)['mean_delta'], .05)
        with self.assertRaises(ValueError):
            compare_runs(a, b[:1], 'meteor', 42)

    def test_generator_never_receives_reference_and_empty_retrieval_is_recorded(self):
        class Generator:
            def generate(self, question, context, metadata, **kwargs):
                assert 'SECRET' not in question + context + str(metadata) + str(kwargs)
                return {'lead': 'lead', 'conclusion': 'end'}
        def scorer(predictions, references):
            return {'per_sample': [{'meteor': .2, 'rouge': .3} for _ in predictions]}
        rows = [{'id': '1', 'question': 'Q', 'contexts': [{'text': 'law'}], 'reference_answer': 'SECRET'},
                {'id': '2', 'question': 'Q2', 'contexts': [], 'reference_answer': 'SECRET'}]
        result = list(evaluate_rows(rows, Generator(), scorer, {}, 1, 42, .5))
        self.assertEqual(result[0]['meteor'], .2)
        self.assertEqual(result[1]['status'], 'empty_retrieval')
        self.assertEqual(result[1]['meteor'], 0)


if __name__ == '__main__':
    unittest.main()
