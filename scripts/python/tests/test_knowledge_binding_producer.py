import tempfile, subprocess, unittest
from pathlib import Path
from scripts.python.knowledge_binding_producer import produce_binding, validate_binding_evidence

class KnowledgeBindingProducerTests(unittest.TestCase):
    def test_rereads_accepted_source_at_revision(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'docs').mkdir(); (root/'docs/a.md').write_text('A',encoding='utf-8')
            for c in [('git','init'),('git','config','user.email','a@b'),('git','config','user.name','a'),('git','add','.'),('git','commit','-m','x')]: subprocess.run(c,cwd=root,check=True,capture_output=True)
            rev=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
            b={'status':'shadow_ready','freeze_state':'unfrozen','request_id':'r','snapshot':{'commit':rev}}
            out=produce_binding(root,b,{'request_id':'r','accepted':[{'path':'docs/a.md'}]})
            self.assertEqual(out['evidence'][0]['path'],'docs/a.md')
    def test_missing_source_fails_closed(self):
            with self.assertRaises(ValueError): produce_binding(Path('.'),{'status':'shadow_ready','freeze_state':'unfrozen','request_id':'r','snapshot':{'commit':'x'}},{'request_id':'r','accepted':[{'path':'x'}]})

    def test_real_decision_set_shape_is_consumed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'docs').mkdir(); (root/'docs/a.md').write_text('A',encoding='utf-8')
            for c in [('git','init'),('git','config','user.email','a@b'),('git','config','user.name','a'),('git','add','.'),('git','commit','-m','x')]: subprocess.run(c,cwd=root,check=True,capture_output=True)
            rev=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
            b={'status':'shadow_ready','freeze_state':'unfrozen','request_id':'r','snapshot':{'commit':rev},'candidates':[{'path':'docs/a.md'}]}
            out=produce_binding(root,b,{'request_id':'r','decisions':[{'decision':'accepted','candidate':{'path':'docs/a.md'}}]})
            self.assertEqual(len(out['evidence']),1)
            validate_binding_evidence(root,b,out)
