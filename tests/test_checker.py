import copy
import json
import unittest
from pathlib import Path

from checker import Replay, Lost, StageError, check

ROOT = Path(__file__).resolve().parents[1]


def sample(number):
    root = ROOT / 'testcases' / 'samples'
    return json.loads((root/f'{number:02}.in.json').read_text()), json.loads((root/f'{number:02}.out.json').read_text())


class CheckerTests(unittest.TestCase):
    def test_all_published_fixtures_replay(self):
        paths = sorted((ROOT/'testcases').glob('*/*.in.json'))
        self.assertEqual(len(paths),39)
        for path in paths:
            with self.subTest(stage=path.name, suite=path.parent.name):
                stage = json.loads(path.read_text())
                answer = json.loads(path.with_name(path.name.replace('.in.','.out.')).read_text())
                self.assertEqual(check(stage,answer)['verdict'],'AC')

    def test_longer_alternative_solution_is_accepted(self):
        stage, _ = sample(1)
        verdict = check(stage,{'status':'solved','actions':['R','L','R','R']})
        self.assertEqual(verdict['verdict'],'AC')
        self.assertEqual(verdict['cost'],4)

    def test_bad_path_is_wa(self):
        stage, _ = sample(1)
        for actions in ([],['R'],['U'],['R','R','L'],['1R']):
            with self.subTest(actions=actions):
                self.assertEqual(check(stage,{'status':'solved','actions':actions})['verdict'],'WA')

    def test_unknown_tokens_and_bad_structure_are_re(self):
        stage, _ = sample(1)
        for answer in ([],{}, {'status':'solved','actions':'RR'},
                       {'status':'solved','actions':['JUMP']},
                       {'status':'solved','actions':[1]}):
            with self.subTest(answer=answer):
                self.assertEqual(check(stage,answer)['verdict'],'RE')

    def test_no_solution_claim_is_wa(self):
        stage, _ = sample(1)
        self.assertEqual(check(stage,{'status':'unsolvable','actions':[]})['verdict'],'WA')

    def test_small_cube_can_stand_on_fragile_and_goal_without_winning(self):
        stage = {'id':'cube-floor-rule','board':['S..T','####','.FG.','....','....'],
                 'bridges':[],'switches':[],
                 'splitters':[{'at':[0,3],'destinations':[[2,0],[4,3]]}]}
        replay = Replay(stage)
        state = replay.initial
        for action in ['R','R','1R','1R']:
            state,_ = replay.step(state,action)
        self.assertTrue(state.split)
        self.assertEqual(state.first,(2,2))
        self.assertFalse(replay.won(state))

    def test_bridge_closing_under_parked_cube_loses(self):
        stage = {'id':'parked-support','board':['S..T','####','B.O.','...G'],
                 'bridges':[{'id':'b1','cells':[[2,0]],'active':True}],
                 'switches':[{'at':[2,2],'effects':[{'bridge':'b1','mode':'off'}]}],
                 'splitters':[{'at':[0,3],'destinations':[[2,0],[3,2]]}]}
        replay = Replay(stage)
        state = replay.initial
        for action in ['R','R']:
            state,_ = replay.step(state,action)
        with self.assertRaises(Lost):
            replay.step(state,'2U')

    def test_shared_switch_targets_have_deterministic_order(self):
        stage = {'id':'shared-effects','board':['SOO.G','####B'],
                 'bridges':[{'id':'b1','cells':[[1,4]],'active':False}],
                 'switches':[{'at':[0,2],'effects':[{'bridge':'b1','mode':'off'}]},
                             {'at':[0,1],'effects':[{'bridge':'b1','mode':'on'}]}],
                 'splitters':[]}
        replay = Replay(stage)
        state,_ = replay.step(replay.initial,'R')
        self.assertEqual(state.bridges,(False,))

    def test_parked_cube_does_not_repress_soft_switch(self):
        stage = {'id':'parked-switch','board':['S..T','####','.O.B','...G'],
                 'bridges':[{'id':'b1','cells':[[2,3]],'active':False}],
                 'switches':[{'at':[2,1],'effects':[{'bridge':'b1','mode':'toggle'}]}],
                 'splitters':[{'at':[0,3],'destinations':[[2,0],[3,3]]}]}
        replay = Replay(stage)
        state = replay.initial
        for action in ['R','R','1R','2L']:
            state,_ = replay.step(state,action)
        self.assertEqual(state.bridges,(True,))

    def test_basic_input_error_is_not_algorithm_wa(self):
        stage,_ = sample(1)
        broken = copy.deepcopy(stage)
        broken['board'][1] = '#'
        with self.assertRaises(StageError):
            check(broken,{'status':'solved','actions':['R','R']})


if __name__ == '__main__':
    unittest.main()
