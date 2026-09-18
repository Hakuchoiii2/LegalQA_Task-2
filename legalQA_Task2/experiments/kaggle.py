"""Build a separate private experiment dataset/kernel, optionally submit with Kaggle CLI."""
import argparse
import base64
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def build(config_path, packages, target, retrieve=False, corpus=None):
    spec = importlib.util.spec_from_file_location('production_build', ROOT / 'kaggle' / 'build.py')
    production = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(production)
    settings = json.loads((ROOT / 'kaggle' / 'settings.json').read_text(encoding='utf-8-sig'))
    settings.update(kernel_slug='dsc2026-legalqa-experiments', kernel_title='DSC2026 LegalQA Experiments',
                    input_dataset_slug=settings['username'] + '/dsc2026-legalqa-experiments-inputs',
                    input_dataset_title='DSC2026 LegalQA Experiments Inputs', retrieve=retrieve)
    target = Path(target)
    target.mkdir(parents=True, exist_ok=False)
    data = target / 'input-dataset'
    kernel = target / 'kernel'
    data.mkdir()
    kernel.mkdir()
    config_path = Path(config_path)
    config = json.loads(config_path.read_text(encoding='utf-8-sig'))
    sys.path.insert(0, str(HERE))
    from run import validate_config
    validate_config(config)
    config['packages'] = 'packages.json'
    shutil.copy2(packages, data / 'packages.json')
    for key in ('split_manifest', 'labels', 'oracle_packages'):
        if config.get(key):
            source = (config_path.parent / config[key]).resolve()
            config[key] = key + '.json'
            shutil.copy2(source, data / config[key])
    if retrieve:
        if not corpus or not Path(corpus).is_file():
            raise ValueError('--retrieve requires --corpus ZIP')
        shutil.copy2(corpus, data / 'corpus.zip')
    (data / 'experiment.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
    metadata = {'id': settings['input_dataset_slug'], 'title': settings['input_dataset_title'],
                'licenses': [{'name': 'other'}]}
    (data / 'dataset-metadata.json').write_text(json.dumps(metadata), encoding='utf-8')
    buffer = io.BytesIO(production.bundle_sources(settings))
    with zipfile.ZipFile(buffer, 'a', compression=zipfile.ZIP_DEFLATED) as archive:
        extras = [HERE / 'run.py', ROOT / 'scripts' / 'run_retrieval.py']
        extras.extend(sorted((ROOT / 'ChanTaooDe--main' / 'src').rglob('*.py')))
        for source in extras:
            archive.write(source, 'legalQA_Task2/' + source.relative_to(ROOT).as_posix())
    source_bundle = buffer.getvalue()
    header = (ROOT / 'kaggle' / 'kernel.template.py').read_text(encoding='utf-8').split('def main()')[0]
    script = (header + (HERE / 'kernel.template.py').read_text(encoding='utf-8')).replace(
        '__SOURCE_BUNDLE__', base64.b64encode(source_bundle).decode()).replace('__RUNTIME_SETTINGS__', repr(settings))
    compile(script, 'run_experiments.py', 'exec')
    (kernel / 'run_experiments.py').write_text(script, encoding='utf-8')
    metadata = {'id': settings['username'] + '/' + settings['kernel_slug'], 'title': settings['kernel_title'],
                'code_file': 'run_experiments.py', 'language': 'python', 'kernel_type': 'script',
                'is_private': 'true', 'enable_gpu': 'true', 'enable_internet': 'true',
                'machine_shape': settings['accelerator'],
                'dataset_sources': [settings['input_dataset_slug'], settings['adapter_slug']],
                'competition_sources': [], 'kernel_sources': [], 'model_sources': []}
    (kernel / 'kernel-metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    (target / 'build_manifest.json').write_text(json.dumps({
        'source_sha256': hashlib.sha256(source_bundle).hexdigest(),
        'input_sha256': hashlib.sha256((data / 'packages.json').read_bytes()).hexdigest(),
        'settings': settings, 'config': config}, indent=2), encoding='utf-8')
    return target


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', default=str(HERE / 'config.json'))
    p.add_argument('--packages', default=str(ROOT / 'inputs' / 'qa_packages_heldout_2026-08-31.json'))
    p.add_argument('--output', default=str(HERE / 'build' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')))
    p.add_argument('--retrieve', action='store_true')
    p.add_argument('--corpus')
    p.add_argument('--push', action='store_true')
    p.add_argument('--update-dataset', action='store_true')
    args = p.parse_args()
    target = build(args.config, args.packages, args.output, args.retrieve, args.corpus)
    print(target)
    if args.push:
        os.environ.setdefault('KAGGLE_ENABLE_OAUTH', 'true')
        command = [sys.executable, '-m', 'kaggle.cli', 'datasets', 'version' if args.update_dataset else 'create',
                   '-p', str(target / 'input-dataset')]
        if args.update_dataset:
            command += ['-m', 'Update LegalQA experiment inputs']
        subprocess.run(command, check=True)
        subprocess.run([sys.executable, '-m', 'kaggle.cli', 'kernels', 'push', '-p', str(target / 'kernel')], check=True)


if __name__ == '__main__':
    main()
