import unittest,sys,tempfile,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from shennong_studio.cli import validate,doctor
from shennong_studio import renderer
class BaselineTests(unittest.TestCase):
 def test_sources_and_paths(self):
  _,cfg=validate('episodes/001-gegen/episode.json');self.assertEqual(cfg['catalogue']['order'],3);self.assertEqual(len(cfg['scenes']),27)
 def test_path_escape_rejected(self):
  with self.assertRaises(ValueError):renderer.project_path(ROOT,'../outside-file')
 def test_draft_does_not_render_as_verified(self):
  d=json.loads((ROOT/'episodes/001-gegen/episode.json').read_text());d['status']='draft'
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'draft.json';p.write_text(json.dumps(d))
   with self.assertRaises(ValueError):validate(p)
 def test_foreign_cwd_and_portable_fonts(self):
  with tempfile.TemporaryDirectory() as td:
   result=subprocess.run([sys.executable,str(ROOT/'scripts/studio.py'),'doctor','episodes/001-gegen/episode.json','--font-profile','portable','--check-hashes'],cwd=td,capture_output=True,text=True)
   self.assertEqual(result.returncode,0,result.stderr)
 def test_frame_can_be_written_without_cloud_tools(self):
  renderer.configure(ROOT/'episodes/001-gegen/episode.json',ROOT,'portable');im=renderer.frame(43.7);self.assertEqual(im.size,(720,1280));self.assertEqual(im.mode,'RGB')
if __name__=='__main__':unittest.main()
