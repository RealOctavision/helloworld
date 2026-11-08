"""Synthetic CPU checks. No real traffic, teacher weights or test months."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np
import torch

import run


def sample(budget, start):
    rng = np.random.default_rng(start)
    n = 20 * budget
    x = np.zeros((n, 3, 30), dtype=np.int32)
    x[:, 0, :12] = rng.integers(0, 500, (n, 12))
    x[:, 1, :12] = rng.choice([-1, 1], (n, 12))
    x[:, 2, :12] = rng.integers(1, 1501, (n, 12))
    return dict(X=x, y=np.repeat(np.arange(20), budget), id=np.arange(start, start+n))


class WideTests(unittest.TestCase):
    def test_architecture_mask_and_gradients(self):
        cfg, _ = run.settings()
        model = run.make_wide_model(run.KIND, 20, 201, cfg)
        self.assertEqual(sum(p.numel() for p in model.parameters()), 77204)
        self.assertEqual(sum(p.numel() for p in run.models.Student(20).parameters()), 20180)
        x = torch.as_tensor(sample(1, 0)['X'], dtype=torch.float32)
        model.eval()
        expected = model(x)
        self.assertEqual(tuple(expected.shape), (20, 20))
        # Padding must not introduce bias-derived features into pooled outputs.
        self.assertTrue(torch.allclose(expected, model(torch.nn.functional.pad(x, (0, 10))), atol=1e-7))
        self.assertTrue(torch.isfinite(model(torch.zeros_like(x))).all())
        torch.nn.functional.cross_entropy(expected, torch.arange(20)).backward()
        for p in model.parameters():
            self.assertIsNotNone(p.grad)
            self.assertTrue(torch.isfinite(p.grad).all())

    def test_actual_training_and_exact_resume(self):
        cfg, _ = run.settings()
        cfg = copy.deepcopy(cfg)
        cfg['training']['batch_size'] = 32
        train, val = sample(3, 0), sample(2, 1000)
        original_factory = run.training.make_model
        with tempfile.TemporaryDirectory() as temp:
            direct, resumed = Path(temp)/'direct', Path(temp)/'resumed'
            kw = dict(cohort=run.COHORT, seed=201, budget=3, lr=0.003,
                      epochs=3, device='cpu', phase='smoke', warmup_epochs=1)
            initial = run.models.state_digest(run.make_wide_model(run.KIND, 20, 201, cfg))
            model, result = run.fit_wide(train, val, cfg, direct, **kw)
            self.assertNotEqual(run.models.state_digest(model), initial)
            self.assertEqual(result['completed_epochs'], 3)
            self.assertEqual(result['teacher_prediction_seconds'], 0)
            self.assertFalse(result['performance_result'])
            self.assertIs(run.training.make_model, original_factory)
            with self.assertRaises(TimeoutError):
                run.fit_wide(train, val, cfg, resumed, time_limit=-1, **kw)
            self.assertIs(run.training.make_model, original_factory)
            restored, other = run.fit_wide(train, val, cfg, resumed,
                                           resume_from=resumed/'last.pt', **kw)
            self.assertEqual(run.models.state_digest(model), run.models.state_digest(restored))
            self.assertEqual(result['validation'], other['validation'])
            for which in ['best', 'last']:
                a = torch.load(direct/f'{which}.pt', weights_only=True)['model']
                b = torch.load(resumed/f'{which}.pt', weights_only=True)['model']
                self.assertTrue(all(torch.equal(a[k], b[k]) for k in a))
            self.assertEqual(run.train_score(model, train, 'cpu')['n'], 60)

    def test_context_and_corruption_guards(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)/'fit'
            run.bind_context(folder, {'channels': run.CHANNELS, 'seed': 201})
            run.bind_context(folder, {'channels': run.CHANNELS, 'seed': 201})
            with self.assertRaises(ValueError):
                run.bind_context(folder, {'channels': run.CHANNELS, 'seed': 202})
            for which in ['best', 'last']:
                (folder/f'{which}.pt').write_bytes(b'checkpoint')
            record = {f'{which}_checkpoint_sha256': run.data.digest(folder/f'{which}.pt')
                      for which in ['best', 'last']}
            (folder/'metrics.json').write_text(json.dumps(record))
            self.assertIsNotNone(run.completed_result(folder))
            (folder/'best.pt').write_bytes(b'corrupt')
            with self.assertRaises(ValueError):
                run.completed_result(folder)

    def test_four_run_plan_and_nested_data(self):
        args = run.parse_args([])
        self.assertEqual([(b, s) for b in args.budgets for s in args.seeds],
                         [(200, 201), (200, 202), (1000, 201), (1000, 202)])
        y = np.repeat(np.arange(20), 1100)
        indices, rank = run.data.sample_per_class(y, 1000, 201, require_full=True)
        self.assertEqual(len(indices[rank < 200]), 4000)
        self.assertEqual(len(indices), 20000)
        self.assertTrue(set(indices[rank < 200]) <= set(indices))
        self.assertEqual(run.summarize([]), {})

    def test_runner_four_fits_and_completed_reuse(self):
        cfg, frozen = run.settings()
        frozen = dict(frozen, epochs=1)
        val = sample(1, 100000)

        def read_split(cohort, name, budget=None):
            self.assertEqual(cohort, run.COHORT)
            if name == 'validation':
                return val
            seed = int(name.removeprefix('main_seed'))
            return sample(budget, seed)

        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            args = run.parse_args(['--device', 'cpu', '--output', temp])
            with mock.patch.object(run.data, 'read_split', side_effect=read_split), \
                 mock.patch.object(run, 'baseline', return_value=None):
                run._run_locked(args, cfg, frozen, output)
                summary = json.loads((output/'summary.json').read_text())
                self.assertEqual(summary['state'], 'completed')
                self.assertEqual(summary['completed_fits'], 4)
                self.assertEqual([r['updates'] for r in summary['runs']], [32, 32, 157, 157])
                self.assertFalse(summary['April_May_evaluated'])
                # Rerunning a completed campaign must not invoke training again.
                with mock.patch.object(run, 'fit_wide', side_effect=AssertionError('Unexpected retraining')):
                    run._run_locked(args, cfg, frozen, output)
                self.assertEqual(json.loads((output/'summary.json').read_text())['runs'], summary['runs'])

    def test_baseline_pairing_rejects_different_samples(self):
        for budget in [200, 1000]:
            if budget == 200:
                paths = run.BASE.glob('main_recovered/training_*/extracted/main_training/fits/M3_s201_n200/metrics.json')
            else:
                paths = run.BASE.glob('continuation_recovered/mixed_n1000/training_*/extracted/continuation/mixed_n1000/training/fits/M3_s201_n1000/metrics.json')
            record = json.loads(next(paths).read_text())
            hashes = {k: record[k] for k in ['train_ids_sha256', 'train_input_sha256',
                                             'train_labels_sha256', 'validation_ids_sha256']}
            self.assertIsNotNone(run.baseline(201, budget, hashes))
            hashes['train_ids_sha256'] = 'different samples'
            with self.assertRaises(ValueError):
                run.baseline(201, budget, hashes)


if __name__ == '__main__':
    unittest.main()
