def main():
    summary = {'status': 'running', 'settings': SETTINGS}
    try:
        os.environ['HF_HOME'] = str(HF_CACHE)
        os.environ['TOKENIZERS_PARALLELISM'] = 'false'
        extract_sources()
        install_dependencies()
        sys.path.insert(0, str(PRODUCTION_ROOT / 'src'))
        from legalqa_baseline.runtime_paths import resolve_input_dataset_root
        data = resolve_input_dataset_root(INPUT_ROOT, SETTINGS['input_dataset_slug'], 'experiment.json')
        adapter = resolve_input_dataset_root(INPUT_ROOT, SETTINGS['adapter_slug'], 'adapter_model.safetensors')
        runtime = json.loads((data / 'experiment.json').read_text())
        # Copy the small experiment input files to working; Kaggle input is read-only.
        import shutil
        run_data = WORKING_ROOT / 'experiment_inputs'
        shutil.copytree(data, run_data)
        if SETTINGS.get('retrieve'):
            run([sys.executable, '-m', 'pip', 'install', '--quiet', 'rank_bm25>=0.2.2',
                 'underthesea>=6.8', 'sentence-transformers>=2.7,<4'])
            corpus_dir = WORKING_ROOT / 'retrieval_corpus'
            with zipfile.ZipFile(run_data / 'corpus.zip') as archive:
                for member in archive.infolist():
                    dest = (corpus_dir / member.filename).resolve()
                    if corpus_dir.resolve() not in dest.parents:
                        raise ValueError('Unsafe corpus zip member')
                archive.extractall(corpus_dir)
            output = run_data / 'retrieved.json'
            run([sys.executable, str(PRODUCTION_ROOT / 'scripts' / 'run_retrieval.py'),
                 '--questions', str(run_data / runtime['packages']), '--corpus', str(corpus_dir),
                 '--cache', str(WORKING_ROOT / 'retrieval_cache'), '--output', str(output),
                 '--top-k', str(runtime['top_k']), '--expand-article'])
            runtime['packages'] = 'retrieved.json'
            (run_data / 'experiment.json').write_text(json.dumps(runtime))
        run([sys.executable, str(PRODUCTION_ROOT / 'experiments' / 'run.py'),
             '--config', str(run_data / 'experiment.json'), '--adapter-path', str(adapter),
             '--output', str(WORKING_ROOT / 'experiment_results')])
        summary['status'] = 'completed'
    except Exception as exc:
        summary.update(status='failed', error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        (WORKING_ROOT / 'experiment_kernel_summary.json').write_text(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
