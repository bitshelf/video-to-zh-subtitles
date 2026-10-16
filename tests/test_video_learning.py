import importlib.util
import argparse
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from pathlib import Path

SRC = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('video_learning', SRC / 'scripts' / 'video_learning.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class VideoLearningTests(unittest.TestCase):
    def test_timestamp(self):
        self.assertEqual(mod.to_seconds('01:02:03.456'), 3723.456)
        self.assertEqual(mod.timestamp(3723.456), '01:02:03,456')
        self.assertEqual(mod.clock(3723.456), '01:02:03')

    def test_roundtrip_import_translation_export(self):
        en = mod.parse_subtitles(SRC / 'examples' / 'sample.en.srt')
        self.assertEqual(len(en), 3)
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d)
            mod.import_cues(en, dest, 'test')
            translations = mod.load_json(SRC / 'examples' / 'sample.translations.json')
            mod.export_translations(dest, translations['items'])
            parsed_zh = mod.parse_subtitles(dest / 'subtitles.zh.srt')
            self.assertEqual(len(parsed_zh), len(en))
            self.assertIn('deferred probe', (dest / 'subtitles.zh.srt').read_text(encoding='utf-8'))
            self.assertIn('[Events]', (dest / 'subtitles.bilingual.ass').read_text(encoding='utf-8'))
            mod.check_translation_items(translations['items'], en)

    def test_mismatched_translation_rejected(self):
        source = mod.parse_subtitles(SRC / 'examples' / 'sample.en.srt')
        with self.assertRaises(RuntimeError):
            mod.check_translation_items([{'id': 3, 'text': 'oops'}], source)

    def test_vtt(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'sample.vtt'
            p.write_text('WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n<c>hello</c>\n', encoding='utf-8')
            got = mod.parse_subtitles(p)
            self.assertEqual(got[0]['text'], 'hello')

    def test_bad_duration(self):
        with self.assertRaises(RuntimeError):
            mod.check_cues([{'id': 1, 'start': 2, 'end': 1, 'text': 'invalid'}])

    def test_invalid_time_values_and_empty_transcript_rejected(self):
        for start, end in [(float('nan'), 2), (0, float('inf')), (True, 2), (-1, 2), (2, 2)]:
            with self.subTest(start=start, end=end), self.assertRaises(RuntimeError):
                mod.check_cues([{'id': 1, 'start': start, 'end': end, 'text': 'text'}])
        with self.assertRaises(RuntimeError):
            mod.check_cues([])

    def test_overlap_report_handles_nested_intervals_and_touching_edges(self):
        cues = [{'id': i + 1, 'start': a, 'end': b, 'text': 'source'}
                for i, (a, b) in enumerate([(0, 10), (1, 2), (3, 4), (10, 12)])]
        mod.check_cues(cues)  # Overlap is reviewable; structural imports still succeed.
        self.assertEqual([f['ids'] for f in mod.source_findings(cues)], [[1, 2], [1, 3]])

    def test_long_duration_is_a_review_warning_not_an_import_error(self):
        cues = [{'id': 1, 'start': 0, 'end': 31, 'text': 'A long cue.'}]
        mod.check_cues(cues)
        self.assertEqual(mod.source_findings(cues)[0]['code'], 'long_duration')

    def test_duration_threshold_is_configurable_with_exact_boundary(self):
        cues = [{'id': 1, 'start': 0, 'end': 12, 'text': 'source'}]
        self.assertEqual(mod.source_findings(cues), [])
        cues[0]['end'] = 12.01
        self.assertEqual(mod.source_findings(cues)[0]['code'], 'long_duration')
        self.assertEqual(mod.source_findings(cues, max_duration=15), [])

    def test_bilingual_order_changes_both_formats_without_changing_chinese_srt(self):
        en = [{'id': 1, 'start': 0, 'end': 4, 'text': 'English line'}]
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            mod.import_cues(en, out, 'fixture')
            for order, expected in [('zh-first', '中文行\nEnglish line'), ('en-first', 'English line\n中文行')]:
                with self.subTest(order=order):
                    mod.export_translations(out, [{'id': 1, 'text': '中文行'}], order=order)
                    bilingual = mod.parse_subtitles(out / 'subtitles.bilingual.srt')
                    self.assertEqual(bilingual[0]['text'], expected)
                    self.assertEqual(mod.parse_subtitles(out / 'subtitles.zh.srt')[0]['text'], '中文行')
                    ass = (out / 'subtitles.bilingual.ass').read_text(encoding='utf-8')
                    dialogue = next(line for line in ass.splitlines() if line.startswith('Dialogue:'))
                    self.assertEqual(dialogue.index('中文行') < dialogue.index('English line'), order == 'zh-first')
                    self.assertIn(r'{\fs32}English line{\r}', dialogue)
                    self.assertEqual(mod.load_json(out / 'translations.json')['order'], order)

    def test_readability_checks_lines_separately_and_cps_over_all_lines(self):
        en = [{'id': 1, 'start': 0, 'end': 4, 'text': 'source'}]
        zh = [{'id': 1, 'text': '<i>' + '中' * 20 + '</i>\n' + '文' * 20}]
        self.assertEqual(mod.readability_findings(en, zh), [])
        zh[0]['text'] = '中' * 29
        finding, = mod.readability_findings(en, zh)
        self.assertEqual((finding['code'], finding['line'], finding['characters']), ('line_width', 1, 29))
        zh[0]['text'] = '中' * 24
        en[0]['end'] = 1
        self.assertEqual(mod.readability_findings(en, zh), [])
        zh[0]['text'] += '文'
        finding, = mod.readability_findings(en, zh)
        self.assertEqual((finding['code'], finding['cps']), ('reading_speed', 25))
        self.assertEqual(mod.readability_findings(en, zh, max_cps=26), [])
        zh[0]['text'] = '<b>中 &amp; 文</b>'
        self.assertEqual(mod.readability_findings(en, zh, max_line_chars=3), [])

    def test_validate_reports_readability_with_selected_limits(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            mod.import_cues([{'id': 1, 'start': 0, 'end': 13, 'text': 'source'}], out, 'fixture')
            mod.export_translations(out, [{'id': 1, 'text': '中' * 29}])
            args = mod.parser().parse_args(['validate', '--out', d, '--for', 'subtitles', '--require-complete'])
            with patch('builtins.print'), self.assertRaises(RuntimeError):
                mod.cmd_validate(args)
            report = mod.load_json(out / 'quality-report.json')
            self.assertEqual(report['source_findings'][0]['code'], 'long_duration')
            self.assertEqual(report['translation_findings'][0]['code'], 'line_width')
            args.max_line_chars = 30
            args.max_duration = 14
            with patch('builtins.print'):
                mod.cmd_validate(args)
            report = mod.load_json(out / 'quality-report.json')
            self.assertEqual(report['warnings'], [])
            self.assertEqual(report['thresholds']['max_duration'], 14)
            args.max_cps = float('nan')
            with self.assertRaises(RuntimeError):
                mod.cmd_validate(args)

    def test_local_glossary_overrides_global_without_truncation_and_affects_validation(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            (out / 'glossary.local.tsv').write_text(
                'English\t中文建议\t说明\nINODE\t本场节点\t本场允许纯中文\n'
                'florp\t专用术语\t保留 florp\nlongnote\t长备注\t' + '注' * 8100 + '\n', encoding='utf-8')
            merged = mod.load_glossary(out)
            self.assertGreater(len(merged), 8000)
            self.assertIn('INODE\t本场节点', merged)
            self.assertNotIn('inode\t索引节点', merged)
            en = [{'id': 1, 'start': 0, 'end': 4, 'text': 'inode florp'}]
            zh = [{'id': 1, 'text': '本场节点及专用术语'}]
            self.assertEqual([f['term'] for f in mod.term_findings(en, zh, out)], ['florp'])
            self.assertEqual([f['term'] for f in mod.term_findings(en, zh)], ['inode'])
            mod.import_cues(en, out, 'fixture')
            mod.export_translations(out, zh)
            report = mod.load_json(out / 'quality-report.json')
            self.assertIn('florp', [f.get('term') for f in report['translation_findings']])

    def test_translate_reuses_hash_across_batches_and_honors_order_and_glossary(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            mod.import_cues(mod.parse_subtitles(SRC / 'examples' / 'sample.en.srt'), out, 'fixture')
            (out / 'glossary.local.tsv').write_text('probe\t本场探测\t\n', encoding='utf-8')
            translations = mod.load_json(SRC / 'examples' / 'sample.translations.json')['items']
            answers = [mod.json.dumps({'items': [item]}) for item in translations]
            args = mod.parser().parse_args(['translate', '--out', d, '--batch-size', '1', '--order', 'en-first'])
            with patch.object(mod, 'config_llm'), patch.object(mod, 'call_llm', side_effect=answers) as llm, \
                    patch.object(mod, 'fingerprint', wraps=mod.fingerprint) as fingerprint:
                mod.cmd_translate(args)
            self.assertEqual(fingerprint.call_count, 2)  # Initial snapshot and pre-export source check.
            self.assertIn('本场探测', mod.json.loads(llm.call_args.args[0][1]['content'])['glossary'])
            self.assertFalse((out / 'translations.partial.json').exists())
            self.assertEqual(mod.load_json(out / 'translations.json')['order'], 'en-first')

    def test_translate_refuses_source_changed_during_api_calls_and_keeps_partial(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            cues = mod.parse_subtitles(SRC / 'examples' / 'sample.en.srt')
            mod.import_cues(cues, out, 'fixture')
            translations = mod.load_json(SRC / 'examples' / 'sample.translations.json')['items']
            def change_source(*args, **kwargs):
                mod.save_json(out / 'transcript.json', {'cues': [{**cue, 'text': 'changed'} for cue in cues]})
                return mod.json.dumps({'items': translations})
            args = mod.parser().parse_args(['translate', '--out', d])
            with patch.object(mod, 'config_llm'), patch.object(mod, 'call_llm', side_effect=change_source), \
                    self.assertRaises(RuntimeError):
                mod.cmd_translate(args)
            self.assertFalse((out / 'translations.json').exists())
            self.assertEqual(mod.load_json(out / 'translations.partial.json')['source_fingerprint'], mod.fingerprint(cues))

    def test_repetition_report_preserves_cues_and_reports_whole_run(self):
        cues = [{'id': i + 1, 'start': i * 3, 'end': i * 3 + 3,
                 'text': 'They have a lot of great software.'} for i in range(12)]
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            mod.import_cues(cues, out, 'ASR fixture')
            report = mod.load_json(out / 'quality-report.json')
            self.assertEqual(report['source_findings'][0]['ids'], list(range(1, 13)))
            self.assertEqual(mod.get_source(out), cues)

    def test_repetition_ignores_short_responses_short_runs_and_distant_repeats(self):
        for sentence, count, stride in [('Yes.', 20, 1), ('They have a lot of great software.', 4, 1),
                                         ('They have a lot of great software.', 8, 10)]:
            cues = [{'id': i + 1, 'start': i * stride, 'end': i * stride + 1,
                     'text': sentence} for i in range(count)]
            self.assertEqual(mod.source_findings(cues), [])

    def test_term_integrity_reports_global_and_local_loss(self):
        texts = ['I/O inode 40 KB 0x50 ext4 AF_INET6 eMMC'] + ['A normal sentence.'] * 5 + ['I/O']
        en = [{'id': i + 1, 'start': i, 'end': i + 1, 'text': text} for i, text in enumerate(texts)]
        zh = [{**c, 'text': 'O 调度器 e 更新 B 数据 0x500 ext40 AF_INET60 MMC'} for c in en]
        zh[-1]['text'] = 'I/O'
        findings = {f['term']: f for f in mod.term_findings(en, zh)}
        for term in ['inode', '40 KB', '0x50', 'ext4', 'AF_INET6', 'eMMC']:
            self.assertEqual(findings[term]['code'], 'missing_term')
        self.assertEqual(findings['I/O']['code'], 'local_term_loss')
        self.assertEqual(findings['I/O']['ids'], [1])
        self.assertNotIn('normal', findings)

    def test_terms_may_move_to_neighboring_cues_with_chinese_boundaries(self):
        en = [{'id': 1, 'start': 0, 'end': 1, 'text': 'Today we use I/O, inode and 40 KB.'},
              {'id': 2, 'start': 1, 'end': 2, 'text': 'This is useful.'}]
        zh = [{**en[0], 'text': '今天讨论其用法。'},
              {**en[1], 'text': '使用I/O与inode，大小为40KB。'}]
        self.assertEqual(mod.term_findings(en, zh), [])

    def test_quantity_keeps_value_and_unit_together_and_preserves_byte_case(self):
        en = [{'id': 1, 'start': 0, 'end': 1, 'text': 'The size is 40 KB.'}]
        for text in ['40 个条目，另有 8 KB。', '大小为 40 kb。', '大小为 400KB。']:
            with self.subTest(text=text):
                findings = mod.term_findings(en, [{**en[0], 'text': text}])
                self.assertEqual(findings[0]['term'], '40 KB')
                self.assertEqual(findings[0]['code'], 'missing_term')
        en[0]['text'] = 'The clock is 2.4 GHz.'
        self.assertEqual(mod.term_findings(en, [{'id': 1, 'text': '时钟为 GHz。'}])[0]['term'], '2.4 GHz')
        self.assertEqual(mod.term_findings(en, [{'id': 1, 'text': '时钟为2.4GHz。'}]), [])

    def test_import_rejects_wrong_fingerprint_even_with_override_before_writing(self):
        cues = mod.parse_subtitles(SRC / 'examples' / 'sample.en.srt')
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            mod.import_cues(cues, out, 'fixture')
            items = mod.load_json(SRC / 'examples' / 'sample.translations.json')['items']
            mod.export_translations(out, items)
            original = (out / 'translations.json').read_bytes()
            incoming = out / 'incoming.json'
            mod.save_json(incoming, {'source_fingerprint': mod.fingerprint([{**cues[0], 'text': 'different'}] + cues[1:]),
                                     'items': items})
            with self.assertRaises(RuntimeError):
                mod.cmd_import_translations(argparse.Namespace(path=str(incoming), out=d, allow_unbound=True))
            self.assertEqual((out / 'translations.json').read_bytes(), original)

    def test_import_requires_fingerprint_or_explicit_legacy_override(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            mod.import_cues(mod.parse_subtitles(SRC / 'examples' / 'sample.en.srt'), out, 'fixture')
            incoming = out / 'incoming.json'
            data = mod.load_json(SRC / 'examples' / 'sample.translations.json')
            data.pop('source_fingerprint', None)
            mod.save_json(incoming, data)
            args = argparse.Namespace(path=str(incoming), out=d, allow_unbound=False)
            with self.assertRaises(RuntimeError):
                mod.cmd_import_translations(args)
            self.assertFalse((out / 'subtitles.zh.srt').exists())
            args.allow_unbound = True
            mod.cmd_import_translations(args)
            args.allow_unbound = False
            args.path = str(out / 'translations.json')
            mod.cmd_import_translations(args)  # Bound imports, including same-file re-exports, succeed.

    def test_subtitle_scope_strict_validation_and_overlap_failure_report(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            cues = mod.parse_subtitles(SRC / 'examples' / 'sample.en.srt')
            mod.import_cues(cues, out, 'fixture')
            mod.export_translations(out, mod.load_json(SRC / 'examples' / 'sample.translations.json')['items'])
            args = argparse.Namespace(out=d, require_complete=True, validation_scope='subtitles')
            with patch('builtins.print'):
                mod.cmd_validate(args)
            cues[1]['start'] = cues[0]['end'] - 0.1
            mod.import_cues(cues, out, 'overlap fixture')
            mod.export_translations(out, mod.load_json(SRC / 'examples' / 'sample.translations.json')['items'])
            with patch('builtins.print'), self.assertRaises(RuntimeError):
                mod.cmd_validate(args)
            self.assertEqual(mod.load_json(out / 'quality-report.json')['source_findings'][0]['code'], 'overlap')

    def test_asr_disables_previous_text_and_sets_explicit_fallback(self):
        whisper = MagicMock()
        whisper.return_value.transcribe.return_value = (
            iter([SimpleNamespace(start=0, end=2, text='Real source text.')]), SimpleNamespace())
        with tempfile.TemporaryDirectory() as d, patch.dict('sys.modules', {
                'faster_whisper': SimpleNamespace(WhisperModel=whisper)}):
            media = Path(d) / 'fixture.wav'
            media.touch()
            args = mod.parser().parse_args(['transcribe', str(media), '--out', str(Path(d) / 'out'),
                                            '--device', 'cpu', '--compute-type', 'int8'])
            mod.cmd_transcribe(args)
            whisper.assert_called_once_with('medium', device='cpu', compute_type='int8')
            options = whisper.return_value.transcribe.call_args.kwargs
            self.assertFalse(options['condition_on_previous_text'])
            self.assertEqual(options['no_speech_threshold'], 0.6)
            self.assertEqual(options['temperature'], (0.0, 0.2, 0.4, 0.6, 0.8, 1.0))

    def test_analyze_synthesizes_all_chunks_and_keeps_evidence(self):
        cues = [{'id': i + 1, 'start': i * 5, 'end': i * 5 + 4,
                 'text': 'technical evidence ' * 30} for i in range(3)]
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            mod.import_cues(cues, out, 'fixture')
            cards = ['[00:00:00] 机制 A', '[00:00:05] 条件 B', '[00:00:10] 反例 C']
            with patch.object(mod, 'config_llm'), patch.object(
                    mod, 'call_llm', side_effect=cards + ['综合笔记']) as llm:
                mod.cmd_analyze(argparse.Namespace(out=d, chunk_chars=1000, depth='deep'))
            self.assertEqual(llm.call_count, 4)
            final_input = llm.call_args.args[0][1]['content']
            for card in cards:
                self.assertIn(card, final_input)
            self.assertTrue((out / 'notes.zh.md').read_text(encoding='utf-8').endswith('综合笔记\n'))
            run_dir, = (out / 'analysis').iterdir()
            self.assertEqual(len(list(run_dir.glob('chunk-*.md'))), 3)
            self.assertEqual(mod.load_json(run_dir / 'source.json')['source_fingerprint'],
                             mod.fingerprint(cues))

    def test_failed_analysis_preserves_notes_and_completed_chunks(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            mod.import_cues(mod.parse_subtitles(SRC / 'examples' / 'sample.en.srt'), out, 'fixture')
            (out / 'notes.zh.md').write_text('人工笔记', encoding='utf-8')
            with patch.object(mod, 'config_llm'), patch.object(
                    mod, 'call_llm', side_effect=['证据卡', RuntimeError('provider failure')]):
                with self.assertRaises(RuntimeError):
                    mod.cmd_analyze(argparse.Namespace(out=d, chunk_chars=1000, depth='standard'))
            self.assertEqual((out / 'notes.zh.md').read_text(encoding='utf-8'), '人工笔记')
            self.assertEqual(len(list((out / 'analysis').glob('*/chunk-*.md'))), 1)

    def test_hierarchical_synthesis_bounds_inputs_and_keeps_all_cards(self):
        cards = [str(i) * 40 for i in range(5)]
        with tempfile.TemporaryDirectory() as d, patch.object(
                mod, 'call_llm', side_effect=['摘要甲', '摘要乙', '摘要丙', '综合']) as llm:
            result = mod.synthesize_reports(cards, 'policy', 'standard', 100, Path(d))
            self.assertEqual(result, '综合')
            inputs = [call.args[0][1]['content'] for call in llm.call_args_list]
            self.assertTrue(all(len(text) <= 100 for text in inputs))
            for card in cards:
                self.assertTrue(any(card in text for text in inputs[:3]))
            self.assertIn('摘要甲', inputs[-1])
            self.assertIn('摘要丙', inputs[-1])

    def test_unmergeable_summaries_stop_without_api_calls(self):
        with tempfile.TemporaryDirectory() as d, patch.object(mod, 'call_llm') as llm:
            with self.assertRaises(RuntimeError):
                mod.synthesize_reports(['x' * 60, 'y' * 60], '', 'quick', 100, Path(d))
            llm.assert_not_called()


if __name__ == '__main__':
    unittest.main()
