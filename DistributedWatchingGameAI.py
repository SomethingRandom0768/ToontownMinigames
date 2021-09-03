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
            self.gameFSM = ClassicFSM.ClassicFSM('DistributedWatchingGameAI', [State.State('inactive', self.enterInactive, self.exitInactive, ['play']), State.State('play', self.enterPlay, self.exitPlay, ['cleanup']), State.State('cleanup', self.enterCleanup, self.exitCleanup, ['inactive'])], 'inactive', 'inactive')
            self.addChildGameFSM(self.gameFSM)
            self.gameWon = False
            self.timeTakenToWin = 0
            self.jellybeansTaken = 0

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
    
    def changeStatusToWin(self):
        self.gameWon = True
        self.timeTakenToWin = self.getCurrentGameTime()
        print('The time won is ' + str(50 - self.timeTakenToWin))
        self.gameOver()
    
    def changeStatusToLoss(self):
        self.timeTakenToLose = self.getCurrentGameTime()
        print('The time lost is ' + str(50 - self.timeTakenToLose))
        self.gameOver()
    
    def reduceJellybeans(self, numbertoLower):
        self.jellybeansTaken += numbertoLower
        print("Lowering the amount of jellybeans the player has by 5. Current jellybean count is: " + str(self.jellybeansTaken))

    def gameOver(self):
        self.notify.debug('gameOver')
        self.gameFSM.request('cleanup')

        # Faster the player wins, the more jellybeans they get. The more time they take, the less they get.
        if self.gameWon:
            for avId in self.avIdList:
                if self.jellybeansTaken:
                    self.scoreDict[avId] = ( (WTGG.GameTime - self.timeTakenToWin) - self.jellybeansTaken)
                else:
                    self.scoreDict[avId] = (WTGG.GameTime - self.timeTakenToWin)
        else:
            for avId in self.avIdList:
                self.scoreDict[avId] = 15 

        DistributedMinigameAI.DistributedMinigameAI.gameOver(self)

    def enterInactive(self):
        self.notify.debug('enterInactive')

    def exitInactive(self):
        pass

    def enterPlay(self):
        self.notify.debug('enterPlay')
        taskMgr.doMethodLater(WTGG.GameTime, self.timerExpired, self.taskName('gameTimer'))

    def timerExpired(self, task):
        '''Game ends once the timer is done.'''
        self.notify.debug("timer expired")
        self.gameOver()
        return Task.done

    def exitPlay(self):
        pass

    def enterCleanup(self):
        self.notify.debug('enterCleanup')
        taskMgr.remove(self.taskName('gameTimer'))
        self.gameFSM.request('inactive')

    def exitCleanup(self):
        pass
