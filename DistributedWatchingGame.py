from direct.fsm import ClassicFSM, State
from direct.fsm import State
from panda3d.core import *
from toontown.toonbase.ToonBaseGlobal import *
from DistributedMinigame import *
from toontown.toonbase import TTLocalizer
from toontown.minigame import CogThiefGameToonSD
from toontown.safezone import Walk
from toontown.toonbase import ToontownTimer
from toontown.minigame import CogThiefWalk
from toontown.minigame import WatchingGameGlobals
from direct.interval.IntervalGlobal import Wait, LerpFunctionInterval, LerpHprInterval, Sequence, Parallel, Func, SoundInterval, ActorInterval, ProjectileInterval, Track, LerpScaleInterval, WaitInterval, LerpPosHprInterval
WTGG = WatchingGameGlobals

class DistributedWatchingGame(DistributedMinigame):

    def __init__(self, cr):
        DistributedMinigame.__init__(self, cr)
        self.gameFSM = ClassicFSM.ClassicFSM('DistributedWatchingGame', 
        [State.State('off', self.enterOff, self.exitOff, ['play']), 
        State.State('play', self.enterPlay, self.exitPlay, ['cleanup']), 
        State.State('cleanup', self.enterCleanup, self.exitCleanup, [])], 'off', 'cleanup')
        self.addChildGameFSM(self.gameFSM)

        # How fast do we want the toon to go?
        self.ToonSpeed = 9.0

        # Variable we'll need for the Cog.
        self.CogLookingBack = False

        # Variable we'll need for if the player won. Depending on this, the text when the game ends will change.
        self.gameWon = False

        # Variable for whether we want to walk in an orthographic way. Obviously, we set it to 0 because ortho-walk isn't what we're goin for.
        self.useOrthoWalk = base.config.GetBool('cog-thief-ortho', 0)

        self.walkStateData = Walk.Walk('walkDone')

        self.__textGen = TextNode('cogThiefGame')
        self.__textGen.setFont(ToontownGlobals.getSignFont())
        self.__textGen.setAlign(TextNode.ACenter)

    def getTitle(self):
        '''Gives the title of the game. '''
        return TTLocalizer.WatchingGameTitle

    def getInstructions(self):
        '''Gives off the instructions that the players will read. Probably gives it to the AI to display.'''
        return TTLocalizer.WatchingGameInstructions

    def getMaxDuration(self):
        '''Not exactly sure what this is used for. '''
        return 10

    def load(self):
        self.notify.debug("loading")
        DistributedMinigame.load(self)

        # Loading up the music and the room that we're going to use.
        self.music = base.loader.loadMusic('phase_10/audio/bgm/Crashed_Cashbot_Trainyard.ogg')
        
        self.room = loader.loadModel("phase_10/models/cashbotHQ/ZONE17a.bam")
        self.room.setPosHpr(0, 0, 0, 0, 0, 0)
        self.room.setScale(1.0)

        # Elevator that looks like the spawn area.
        self.elevator = loader.loadModel("phase_11/models/lawbotHQ/LB_ElevatorScaled.bam")
        self.elevator.setPosHpr(-22, -98, 0, 90, 0, 0)
        self.elevator.setScale(1.0)

        # Place with the console and where the minigame should end.
        self.consoleRoom = loader.loadModel("phase_10/models/cashbotHQ/ZONE03a.bam")
        self.consoleRoom.setPosHpr(0.75, 142, 0, 180, 0, 0)
        self.consoleRoom.setScale(1.0)
        


        # Stealing from Cog Thief because they really have everything I need in terms of animation.
        self.toonSDs = {}
        avId = self.localAvId
        toonSD = CogThiefGameToonSD.CogThiefGameToonSD(avId, self)
        self.toonSDs[avId] = toonSD
        toonSD.load()

        # Loading up the timer that we'll need. Also, positioning to the top right corner and hiding it.

        self.timer = ToontownTimer.ToontownTimer()
        self.timer.posInTopRightCorner()
        self.timer.hide()

        # load the jellybean jar image
        # this model comes from PurchaseBase
        purchaseModels = loader.loadModel("phase_4/models/gui/purchase_gui")
        self.jarImage = purchaseModels.find("**/Jar")
        self.jarImage.reparentTo(hidden)        

       # reward display
        self.rewardPanel = DirectLabel(
            parent = hidden,
            relief = None,
            pos = (1.16, 0.0, 0.45),
            scale = .65,
            text = '',
            text_scale = 0.2,
            text_fg = (0.95, 0.95, 0, 1),
            text_pos = (0, -.13),
            text_font = ToontownGlobals.getSignFont(),
            image = self.jarImage,
            )
        self.rewardPanelTitle = DirectLabel(
            parent = self.rewardPanel,
            relief = None,
            pos = (0, 0, 0.06),
            scale = .08,
            text = TTLocalizer.CannonGameReward,
            text_fg = (.95,.95,0,1),
            text_shadow = (0,0,0,1),
            )

            # Random comment, who knew every minigame just used the same text from the Cannon Game.

    def unload(self):
        '''Here we delete everything so that it doesn't stick around after the game.'''
        self.notify.debug('unload')
        DistributedMinigame.unload(self)
        self.removeChildGameFSM(self.gameFSM)
        del self.gameFSM
        del self.music
        self.room.removeNode()
        self.elevator.removeNode()
        self.consoleRoom.removeNode()
        del self.room
        del self.elevator
        del self.consoleRoom
        del self.toonSDs
        self.timer.destroy()
        del self.timer
        self.rewardPanel.destroy()
        del self.rewardPanel
        self.jarImage.removeNode()
        del self.jarImage


    def onstage(self):
        self.notify.debug('onstage')
        DistributedMinigame.onstage(self)

        # Loading up the place so we can actually see stuff.
        self.room.reparentTo(render)
        self.elevator.reparentTo(render)
        self.consoleRoom.reparentTo(render)

        # Let the player see the toon. 
        playerToon = base.localAvatar
        playerToon.reparentTo(render)
        self.__placeToon(self.localAvId)
        playerToon.setSpeed(0, 0)
        base.localAvatar.attachCamera()

        toonSD = self.toonSDs[self.localAvId]
        toonSD.enter()
        toonSD.fsm.request('init') # Setting the toon's state to normal so they are just standing still.
        
        # Stopping the player from any input for now.
        self.stopGameWalk()

        # Start the music, we need the baller music while infiltrating Cashbot HQ.
        base.playMusic(self.music, looping = 1, volume = 0.5 )


    def offstage(self):
        '''Welp, now that it's time to start leaving, hide everything! No one needs to know this game existed.'''
        self.notify.debug('offstage')
        DistributedMinigame.offstage(self)
        self.room.hide()
        self.elevator.hide()
        self.consoleRoom.hide()
        self.music.stop()

        self.timer.reparentTo(hidden)

    def handleDisabledAvatar(self, avId):
        self.notify.debug('handleDisabledAvatar')
        self.notify.debug('avatar ' + str(avId) + ' disabled')
        DistributedMinigame.handleDisabledAvatar(self, avId)

    def setGameReady(self):
        if not self.hasLocalToon:
            return
        self.notify.debug('setGameReady')
        if DistributedMinigame.setGameReady(self):
            return

    def setGameStart(self, timestamp):
        if not self.hasLocalToon:
            return
        self.notify.debug('setGameStart')
        DistributedMinigame.setGameStart(self, timestamp)
        self.rewardPanel.reparentTo(base.a2dTopRight)
        self.timer.show()
        self.timer.countdown(WTGG.GameTime, self.__gameTimerExpired)
        self.gameFSM.request('play')

    def enterOff(self):
        self.notify.debug('enterOff')

    def exitOff(self):
        pass

    def enterPlay(self):
        self.notify.debug('enterPlay')

        self.walkStateData.enter()
        self.walkStateData.fsm.request('walking')

    def exitPlay(self):
        self.walkStateData.exit()
        pass

    def enterCleanup(self):
        self.notify.debug('enterCleanup')

    def exitCleanup(self):
        pass

    # This is where all my personally created (and some copied over from Cog Thief) functions start.

    def startGameWalk(self):
        if self.useOrthoWalk:
            self.gameWalk.start()
        else:
            self.gameWalk.enter()
            self.gameWalk.fsm.request('walking')

    def stopGameWalk(self):
        if self.useOrthoWalk:
            self.gameWalk.stop()
        else:
            self.gameWalk.exit()

    def destroyGameWalk(self):
        self.notify.debug('destroyOrthoWalk')
        if self.useOrthoWalk:
            self.gameWalk.destroy()
            del self.gameWalk
        else:
            self.notify.debug('TODO destroyGameWalk')

    def initGameWalk(self):
        self.notify.debug('startOrthoWalk')
        if self.useOrthoWalk:

            def doCollisions(oldPos, newPos, self = self):
                x = bound(newPos[0], CTGG.StageHalfWidth, -CTGG.StageHalfWidth)
                y = bound(newPos[1], CTGG.StageHalfHeight, -CTGG.StageHalfHeight)
                newPos.setX(x)
                newPos.setY(y)
                return newPos

            orthoDrive = OrthoDrive(self.ToonSpeed, customCollisionCallback=doCollisions, instantTurn=True)
            self.gameWalk = OrthoWalk(orthoDrive, broadcast=not self.isSinglePlayer())
        else:
            self.gameWalk = CogThiefWalk.CogThiefWalk('walkDone')
            forwardSpeed = self.ToonSpeed / 2.0
            base.mouseInterfaceNode.setForwardSpeed(forwardSpeed)
            multiplier = forwardSpeed / ToontownGlobals.ToonForwardSpeed
            base.mouseInterfaceNode.setRotateSpeed(ToontownGlobals.ToonRotateSpeed * 4)


    def __placeToon(self, avId):
        """Placing a toon in the starting position."""
        toon = self.getAvatar(avId)
        toon.setPos(-16,-97,0) # It doesn't matter since the game is single player.
        toon.setHpr(270,0,0)

    def __gameTimerExpired(self):
        self.notify.debug('game timer expired')
        # self.showResults()

    def showResults(self):
        self.stopGameWalk()
        result = ''

        if self.gameWon == False:
            result = TTLocalizer.WatchingGameLost
        else:
            result = TTLocalizer.WatchingGameWon
        

        perfectTextSubnode = hidden.attachNewNode(self.__genText(result))
        perfectText = hidden.attachNewNode('perfectText')
        perfectTextSubnode.reparentTo(perfectText)
        frame = self.__textGen.getCardActual()
        offsetY = -abs(frame[2] + frame[3]) / 2.0
        perfectTextSubnode.setPos(0, 0, offsetY)
        perfectText.setColor(1, 0.1, 0.1, 1)

        def fadeFunc(t, text = perfectText):
            text.setColorScale(1, 1, 1, t)

        def destroyText(text = perfectText):
            text.removeNode()

        def safeGameOver(self = self):
            if not self.frameworkFSM.isInternalStateInFlux():
                self.gameOver()

        textTrack = Sequence(Func(perfectText.reparentTo, aspect2d), Parallel(LerpScaleInterval(perfectText, duration=0.5, scale=0.3, startScale=0.0), LerpFunctionInterval(fadeFunc, fromData=0.0, toData=1.0, duration=0.5)), Wait(2.0), Parallel(LerpScaleInterval(perfectText, duration=0.5, scale=1.0), LerpFunctionInterval(fadeFunc, fromData=1.0, toData=0.0, duration=0.5, blendType='easeIn')), Func(destroyText), WaitInterval(0.5), Func(safeGameOver))

        self.resultIval = Parallel(textTrack)
        self.resultIval.start()
            
    
    def __genText(self, text):
        self.__textGen.setText(text)
        return self.__textGen.generate()


