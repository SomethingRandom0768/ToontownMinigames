from direct.fsm import ClassicFSM
from direct.fsm import State
from direct.distributed.ClockDelta import globalClockDelta
from direct.task import Task
from toontown.minigame import DistributedMinigameAI
from toontown.minigame import MinigameGlobals
from toontown.minigame import WatchingGameGlobals
WTGG = WatchingGameGlobals

class DistributedWatchingGameAI(DistributedMinigameAI.DistributedMinigameAI):

    def __init__(self, air, minigameId):
        try:
            self.DistributedWatchingGameAI_initialized
        except:
            self.DistributedWatchingGameAI_initialized = 1
            DistributedMinigameAI.DistributedMinigameAI.__init__(self, air, minigameId)
            self.gameFSM = ClassicFSM.ClassicFSM('DistributedMinigameTemplateAI', [State.State('inactive', self.enterInactive, self.exitInactive, ['play']), State.State('play', self.enterPlay, self.exitPlay, ['cleanup']), State.State('cleanup', self.enterCleanup, self.exitCleanup, ['inactive'])], 'inactive', 'inactive')
            self.addChildGameFSM(self.gameFSM)
            self.gameWon = False

    def generate(self):
        self.notify.debug('generate')
        DistributedMinigameAI.DistributedMinigameAI.generate(self)

    def delete(self):
        self.notify.debug('delete')
        del self.gameFSM
        DistributedMinigameAI.DistributedMinigameAI.delete(self)

    def setGameReady(self):
        self.notify.debug('setGameReady')
        DistributedMinigameAI.DistributedMinigameAI.setGameReady(self)

    def setGameStart(self, timestamp):
        self.notify.debug('setGameStart')
        DistributedMinigameAI.DistributedMinigameAI.setGameStart(self, timestamp)
        self.gameFSM.request('play')

    def setGameAbort(self):
        self.notify.debug('setGameAbort')
        if self.gameFSM.getCurrentState():
            self.gameFSM.request('cleanup')
        DistributedMinigameAI.DistributedMinigameAI.setGameAbort(self)

    def gameOver(self):
        self.notify.debug('gameOver')
        self.gameFSM.request('cleanup')
        DistributedMinigameAI.DistributedMinigameAI.gameOver(self)

    def enterInactive(self):
        self.notify.debug('enterInactive')

    def exitInactive(self):
        pass

    def enterPlay(self):
        self.notify.debug('enterPlay')
        self.gameOver()

    def exitPlay(self):
        pass

    def enterCleanup(self):
        self.notify.debug('enterCleanup')
        self.gameFSM.request('inactive')

    def exitCleanup(self):
        pass