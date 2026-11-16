import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'deploy'))
import importlib.util
import json
import os
import tempfile
import unittest
from unittest.mock import patch
from content_model import load_bundle, validate_bundle
from build_pages import build

ROOT=Path(__file__).resolve().parents[1]


class ContentEditorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.data=load_bundle(ROOT)

    @patch.dict(os.environ,{},clear=True)
    def test_export_changes_render_without_touching_source(self):
        original=(ROOT/'content/site.json').read_bytes()
        self.data['site']['hero']['title']='Новый <заголовок>'
        self.data['site']['global']['seoTitle']='Новый title'
        self.data['site']['global']['phoneRaw']='+79990000000'
        self.data['site']['global']['phone']='+7 (999) 000-00-00'
        self.data['site']['pricing']['items'].append({'name':'Новая операция','price':'от 999 ₽'})
        self.data['site']['districts']['items']=['Новый район']
        self.data['site']['why']['items']=[]
        self.data['articles'].append({'slug':'novaya-statya','heading':'Новая статья','title':'Новый материал','description':'Описание','body':'Текст **статьи**.'})
        path=self.root/'export.json';path.write_text(json.dumps(self.data,ensure_ascii=False))
        build(self.root/'site',content_file=path)
        home=(self.root/'site/index.html').read_text()
        self.assertIn('Новый &lt;заголовок&gt;',home)
        self.assertIn('<title>Новый title</title>',home)
        self.assertIn('Новая операция',home)
        self.assertIn('href="tel:+79990000000"',home)
        self.assertNotIn('<h3>Только оригинал</h3>',home)
        self.assertTrue((self.root/'site/articles/novaya-statya/index.html').exists())
        self.assertEqual((ROOT/'content/site.json').read_bytes(),original)
        self.assertIn('data-api=""',home)

    def test_reject_private_fields_enabling_intake_and_executable_links(self):
        for edit in ('leads','enabled','script','traversal'):
            data=load_bundle(ROOT)
            if edit=='leads':data['leads']=[{'phone':'test'}]
            elif edit=='enabled':data['site']['form']['enabled']=True
            elif edit=='script':data['articles'][0]['body']='[Click](javascript:alert)'
            else:data['articles'][0]['slug']='../../admin'
            with self.subTest(edit=edit),self.assertRaises(ValueError):validate_bundle(data,ROOT)

    def test_invalid_import_does_not_change_source(self):
        spec=importlib.util.spec_from_file_location('apply_content',ROOT/'deploy/apply_content.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        target=self.root/'checkout';(target/'content').mkdir(parents=True);(target/'web').mkdir()
        for name in ('site.json','articles.json'):(target/'content'/name).write_bytes((ROOT/'content'/name).read_bytes())
        (target/'web/index.html').write_bytes((ROOT/'web/index.html').read_bytes())
        module.ROOT=target
        export=self.root/'export.json';data=load_bundle(ROOT);data['site']['global']['phoneRaw']='invalid';export.write_text(json.dumps(data))
        original=(target/'content/site.json').read_bytes()
        with self.assertRaises(ValueError):module.apply(export)
        self.assertEqual((target/'content/site.json').read_bytes(),original)
        data['site']['global']['phoneRaw']='+79990000000';export.write_text(json.dumps(data));module.apply(export)
        self.assertEqual(json.loads((target/'content/site.json').read_text())['global']['phoneRaw'],'+79990000000')
