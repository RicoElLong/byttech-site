import sys
sys.path.insert(0,str(__import__("pathlib").Path(__file__).resolve().parents[1]/"deploy"))
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pages',ROOT/'deploy/build_pages.py')
pages=importlib.util.module_from_spec(spec);spec.loader.exec_module(pages)


class PagesBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.site=Path(self.temp.name)/'site'

    @patch.dict(os.environ,{},clear=True)
    def test_disabled_review_build_articles_and_local_links(self):
        pages.build(self.site)
        articles=json.loads((ROOT/'content/articles.json').read_text())
        for article in articles:
            filename=self.site/'articles'/article['slug']/'index.html'
            html=filename.read_text()
            self.assertEqual(html.count('<h1>'),1)
            self.assertIn(article['title'],html)
            self.assertIn('../../#quiz',html)
            self.assertIn('../../#prices',html)
            self.assertIn('aria-current="page"',html)
        for filename in self.site.rglob('*.html'):
            html=filename.read_text()
            self.assertNotIn('{{OWNER_',html)
            for link in re.findall(r'(?:href|src)="([^"#]+)(?:#[^"]*)?"',html):
                if ':' in link or link.startswith('/'):continue
                target=(filename.parent/link).resolve()
                self.assertTrue(target.exists(),f'{filename}: {link}')
        home=(self.site/'index.html').read_text()
        self.assertIn('data-api=""',home)
        self.assertEqual(home.count('class="quiz-opt"'),26)
        self.assertIn('Отзывы готовятся к публикации',home)
        self.assertNotIn('id="reviewsViewport"',home)
        self.assertTrue((self.site/'assets/washer-brands.webp').is_file())
        self.assertIn('href="./consent.html"',home)
        self.assertIn('href="./privacy.html"',home)
        self.assertIn('data-open-policy',home)
        modal=home.split('<dialog class="policy-dialog"',1)[1].split('</dialog>',1)[0]
        self.assertNotIn('<iframe',modal)
        self.assertNotIn('Проект для проверки оператором',modal)
        self.assertNotIn('Будет указан до включения приёма заявок',modal)
        self.assertNotIn('<a ',modal)
        self.assertIn('12. Заключительные положения и обновления',modal)
        self.assertIn('Политика в отношении обработки персональных данных',modal)
        self.assertIn('Для отправки заявки требуется отдельная галочка выше.',home)
        privacy=(self.site/'privacy.html').read_text()
        self.assertNotIn('servic-bt.ru',privacy)
        self.assertNotIn('info@servic-bt.ru',privacy)
        self.assertIn('Приём заявок через форму БытТех отключён',privacy)
        self.assertIn('pd-2026-11-09-v1',privacy)
        self.assertIn('2. Основные понятия',privacy)
        self.assertIn('12. Заключительные положения и обновления',privacy)

    def test_reviews_need_permission_and_escape_content(self):
        review = {'name':'Анонимный клиент','text':'<b>Спасибо</b>',
                  'date':'17.11.2026','sourceUrl':'https://example.org/review/1','permission':True}
        content=Path(self.temp.name)/'content';content.mkdir()
        (content/'reviews.json').write_text(json.dumps([review]),encoding='utf-8')
        with patch.object(pages,'ROOT',Path(self.temp.name)):
            html=pages.render_reviews((ROOT/'web/index.html').read_text())
            self.assertIn('id="reviewsViewport"',html)
            self.assertIn('&lt;b&gt;Спасибо&lt;/b&gt;',html)
            self.assertNotIn('Отзывы готовятся к публикации',html)
            review['permission']=False
            (content/'reviews.json').write_text(json.dumps([review]),encoding='utf-8')
            with self.assertRaises(ValueError):pages.render_reviews(html)

    @patch.dict(os.environ,{'SITE_URL':'https://example.test/byttech-site'},clear=True)
    def test_configured_production_canonical_and_sitemap(self):
        pages.build(self.site,production=True)
        self.assertEqual((self.site/'sitemap.xml').read_text().count('/articles/'),6)
        html=(self.site/'articles/ne-otzhimaet/index.html').read_text()
        self.assertIn('href="https://example.test/byttech-site/articles/ne-otzhimaet/"',html)
        self.assertNotIn('noindex',html)
        self.assertIn('Sitemap:',(self.site/'robots.txt').read_text())

    @patch.dict(os.environ,{},clear=True)
    def test_no_unconfirmed_domain_for_production(self):
        with self.assertRaises(ValueError):pages.build(self.site,production=True)

    @patch.dict(os.environ,{'REQUEST_API_URL':'https://example.test/api/requests'},clear=True)
    def test_api_requires_document_approval(self):
        with self.assertRaises(ValueError):pages.build(self.site)
