import math
from panda3d.core import CollisionSphere, CollisionNode, Point3, CollisionTube, Vec3, rad2Deg
from direct.showbase.DirectObject import DirectObject
from direct.distributed.ClockDelta import globalClockDelta
from direct.interval.IntervalGlobal import Parallel, SoundInterval, Sequence, Func, LerpScaleInterval
from toontown.suit import Suit
from toontown.suit import SuitDNA
from toontown.toonbase import ToontownGlobals
from toontown.minigame import CogThiefGameGlobals
from toontown.battle.BattleProps import globalPropPool
from toontown.battle.BattleSounds import globalBattleSoundCache

class Watcher(DirectObject):

    def __init__(self, suitType, game):
        '''Watcher for the DistributedWatchingMinigame.'''
        #self.fsm = ClassicFSM.ClassicFSM('Watcher',
        #[State.State('Inactive') ])
        self.suitType = suitType
        self.game = game
        self.suitType = suitType
        self.game = game
        suit = Suit.Suit()
        d = SuitDNA.SuitDNA()
        d.newSuit(suitType)
        suit.setDNA(d)
        suit.loop('neutral', 0)
        self.suit = suit
        self.suit.loop('neutral')
        return

    def cleanup(self):
        self.ignoreAll()
        self.suit.delete()
        self.suit = None
        self.game = None
        return
    
    def rotateCogTowardToon(self):
        if self.suit:
            self.suit.setHpr(540, 0, 0)

    def rotateCogBackward(self):
        if self.suit:
            self.suit.setHpr(0,0,0)

    def returnSuitType(self):
        return self.suitType

    def startWatchAnim(self):
        if self.suit:
            self.suit.loop('neutral')

    
