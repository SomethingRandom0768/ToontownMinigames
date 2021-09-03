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
from toontown.minigame import CogThiefGameGlobals as CTGG
from toontown.minigame import Watcher
from direct.interval.IntervalGlobal import Wait, LerpFunctionInterval, LerpHprInterval, Sequence, Parallel, Func, SoundInterval, ActorInterval, ProjectileInterval, Track, LerpScaleInterval, WaitInterval, LerpPosHprInterval
import math
WTGG = WatchingGameGlobals

class DistributedWatchingGame(DistributedMinigame):
    REWARD_COUNTDOWN_TASK = 'WatchingGameRewardCountdown'
    COG_ROTATE_TASK = 'WatchingGameCogRotations'

    def __init__(self, cr):
        DistributedMinigame.__init__(self, cr)
        self.gameFSM = ClassicFSM.ClassicFSM('DistributedWatchingGame', 
        [State.State('off', self.enterOff, self.exitOff, ['play']), 
        State.State('play', self.enterPlay, self.exitPlay, ['cleanup']), 
        State.State('cleanup', self.enterCleanup, self.exitCleanup, [])], 'off', 'cleanup')
        self.addChildGameFSM(self.gameFSM)

        # Using this variable to silence any errors. Could write my own SD in the future but I'm good for now.
        self.ToonSpeed = 0

        # Variable we'll need for the Cog.
        self.CogLookingBack = False

        # Variable we'll need to detect if the player is moving.
        self.toonMoving = False

        # Variable we'll need for if the player won. Depending on this, the text when the game ends will change.
        self.gameWon = False

        self.cogInfo = {}

        # The amount of jellybeans to remove from the jelly bean jar whenever you touch the cog. Unused variable.
        # self.jellybeansToTake = 0

        # Variable for whether we want to walk in an orthographic way. Obviously, we set it to 0 because ortho-walk isn't what we're goin for.
        self.useOrthoWalk = base.config.GetBool('cog-thief-ortho', 0)

        self.walkStateData = Walk.Walk('walkDone')

        self.__textGen = TextNode('cogThiefGame')
        self.__textGen.setFont(ToontownGlobals.getSignFont())
        self.__textGen.setAlign(TextNode.ACenter)

    def getTitle(self):
        '''Gives the title of the game. '''
        #return TTLocalizer.WatchingGameTitle
        return "Red Light, Green Light"

    def getInstructions(self):
        '''Gives off the instructions that the players will read. Probably gives it to the AI to display.'''
        #return TTLocalizer.WatchingGameInstructions
        return "The Toon Resistance needs your help to start Crash Cashbot! Touch the console in the room at the far end to lower Cashbot HQ's defenses but watch out for that cog and don't let them see you moving! Use the arrow keys to move around."

    def getMaxDuration(self):
        '''Not exactly sure what this is used for. '''
        return WTGG.GameTime

    def load(self):
        
        self.notify.debug("loading")
        DistributedMinigame.load(self)

        self.initCogInfo()

        # Loading up the music and the room that we're going to use.
        self.music = base.loader.loadMusic('phase_10/audio/bgm/Crashed_Cashbot_Trainyard.ogg')
        self.cogWarning = base.loader.loadSfx('phase_3.5/audio/dial/COG_VO_question.ogg')
        self.consoleActivating = base.loader.loadSfx('phase_11/audio/sfx/LB_capacitor_discharge_3.ogg') 
        self.sndRewardTick = base.loader.loadSfx('phase_3.5/audio/sfx/tick_counter.ogg')
        
        self.room = loader.loadModel("phase_10/models/cashbotHQ/ZONE17a.bam")
        self.room.setPosHpr(0, 0, 0, 0, 0, 0)
        self.room.setScale(1.0)

        # Elevator that looks like the spawn area.
        self.elevator = loader.loadModel("phase_11/models/lawbotHQ/LB_ElevatorScaled.bam")
        self.elevatorDoorCollision = self.elevator.find("**/elevator_Door_collisions*")
        self.elevatorDoorCollision.removeNode()
        self.elevator.setPosHpr(-22, -98, 0, 90, 0, 0)
        self.elevator.setScale(1.0)

        # Place with the console and where the minigame should end.
        self.consoleRoom = loader.loadModel("phase_10/models/cashbotHQ/ZONE03a.bam")
        self.consoleRoom.setPosHpr(0.75, 142, 0, 180, 0, 0)
        self.consoleRoom.setScale(1.0)
        
        # We'll put in the console that the player touches to end the minigame.
        self.console = loader.loadModel("phase_10/models/cogHQ/CBCraneControls.bam")
        self.consoleLever = loader.loadModel("phase_10/models/cogHQ/CBCraneStick.bam")
        self.console.setPosHpr(0, 142, 0, 360, 0, 0)
        self.consoleLever.setPosHpr(0, 143.75, 3, 0, 25, 0)
        self.console.setScale(1.0)
        self.consoleLever.setScale(1.0)

        # We should add in the collision node to this barrel that the player will touch to end the game.
        self.barrel = loader.loadModel('phase_4/models/minigames/cogthief_game_gagTank')
        self.barrel.setPosHpr(0, 145, 0, 360, 0, 0)
        self.barrel.setScale(0.5)
        self.barrel.hide()

        self.loadCogs()
        

        collSphere = CollisionSphere(0, 0, 0, 10)
        collSphere.setTangible(0)
        name = 'BarrelSphere'
        collSphereName = self.uniqueName(name)
        collNode = CollisionNode(collSphereName)
        collNode.setFromCollideMask(CTGG.BarrelBitmask)
        #collNode.addSolid(collSphere)
        collNode.addSolid(collSphere)
        colNp = self.barrel.attachNewNode(collNode)
        #colNp.show()
        handler = CollisionHandlerEvent()
        handler.setInPattern('barrelHit-%fn')
        base.cTrav.addCollider(colNp, handler)
        self.accept('barrelHit-' + collSphereName, self.handleEnterBarrel)
        

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
        self.rewardPanel = DirectLabel(parent=hidden, relief=None, pos=(-0.173, -1.2, -0.55), scale=0.65, text='', text_scale=0.2, text_fg=(0.95, 0.95, 0, 1), text_pos=(0, -.13), text_font=ToontownGlobals.getSignFont(), image=self.jarImage)
        self.rewardPanelTitle = DirectLabel(parent=self.rewardPanel, relief=None, pos=(0, 0, 0.06), scale=0.08, text=TTLocalizer.CannonGameReward, text_fg=(0.95, 0.95, 0, 1), text_shadow=(0, 0, 0, 1))

        # Random comment, who knew every minigame just used the same text from the Cannon Game.

    def unload(self):
        '''Here we delete everything so that it doesn't stick around after the game.'''

        taskMgr.remove('rotateCog')
        taskMgr.remove('rotateCogPlayer')
        taskMgr.remove('rotateCogDefault')


        self.notify.debug('unload')
        DistributedMinigame.unload(self)
        self.removeChildGameFSM(self.gameFSM)
        del self.gameFSM
        del self.music
        self.room.removeNode()
        self.elevator.removeNode()
        self.consoleRoom.removeNode()
        self.console.removeNode()
        self.consoleLever.removeNode()
        self.barrel.removeNode()
        self.toonCol.removeNode()
        del self.room
        del self.elevator
        del self.consoleRoom
        del self.console
        del self.consoleLever
        del self.barrel
        del self.toonSDs
        del self.toonCol
        self.timer.destroy()
        del self.timer
        self.rewardPanel.destroy()
        del self.rewardPanel
        self.jarImage.removeNode()
        del self.jarImage
        del self.sndRewardTick


    def onstage(self):
        self.notify.debug('onstage')
        DistributedMinigame.onstage(self)

        # Loading up the place so we can actually see stuff.
        self.room.reparentTo(render)
        self.elevator.reparentTo(render)
        self.consoleRoom.reparentTo(render)
        self.console.reparentTo(render)
        self.consoleLever.reparentTo(render)
        self.barrel.reparentTo(render)

        # Not exactly sure how this works but apparently it loads up the cog model, which is awesome.
        for cogIndex in xrange(self.getNumCogs()):
            suit = self.cogInfo[cogIndex]['suit'].suit
            pos = self.cogInfo[cogIndex]['pos']
            suit.reparentTo(render)
            suit.setPos(pos)
            suit.setHpr(0,0,0)
            # h of 540 is the cog turning towards the player.

            # We're creating a cog collision capsule so that the player won't go through the cog.

            print("The suit type below is the cog:")
            chosenSuitType = self.cogInfo[0]['suit'].returnSuitType()
            print(chosenSuitType)

            if chosenSuitType == 'tbc': # the big cheese
                cogCollisionSphere = CollisionBox( (0,0,7), 2.5, 1, 3)
                cogCollisionSphere.setTangible(1)
                name = 'cogBox'
                cogBoxName = self.uniqueName(name)
                cogCollisionNode = CollisionNode(cogBoxName)
                cogCollisionNode.addSolid(cogCollisionSphere)
                self.cogCol = suit.attachNewNode(cogCollisionNode)
                #self.cogCol.show()
                #handler = CollisionHandlerEvent()
                #handler.setInPattern('cogHit-%fn')
                #base.cTrav.addCollider(self.cogCol, handler)
                #self.accept('cogHit-' + cogBoxName, self.handleEnterCog)
                
            elif chosenSuitType == 'le': # legal eagle 
                cogCollisionSphere = CollisionBox( (0,0,7), 2.5, 1, 6)
                cogCollisionSphere.setTangible(1)
                name = 'cogBox'
                cogBoxName = self.uniqueName(name)
                cogCollisionNode = CollisionNode(cogBoxName)
                cogCollisionNode.addSolid(cogCollisionSphere)
                self.cogCol = suit.attachNewNode(cogCollisionNode)
                
            elif chosenSuitType == 'ls': # loan shark
                cogCollisionSphere = CollisionBox((0,0,7), 1.5, 1, 6)
                cogCollisionSphere.setTangible(1)
                name = 'cogBox'
                cogBoxName = self.uniqueName(name)
                cogCollisionNode = CollisionNode(cogBoxName)
                cogCollisionNode.addSolid(cogCollisionSphere)
                self.cogCol = suit.attachNewNode(cogCollisionNode)

                
            elif chosenSuitType == 'nc' or chosenSuitType == 'ms': # number cruncher or mover & shaker
                cogCollisionSphere = CollisionBox( (0,0,7), 1.5, 1, 5)
                cogCollisionSphere.setTangible(1)
                name = 'cogBox'
                cogBoxName = self.uniqueName(name)
                cogCollisionNode = CollisionNode('cogCollision')
                cogCollisionNode.addSolid(cogCollisionSphere)
                self.cogCol = suit.attachNewNode(cogCollisionNode)

              
            elif chosenSuitType == 'mm': # micromanager
                cogCollisionSphere = CollisionBox( (0,0,2), 1.5, 1, 1)
                cogCollisionSphere.setTangible(1)
                name = 'cogBox'
                cogBoxName = self.uniqueName(name)
                cogCollisionNode = CollisionNode('cogCollision')
                cogCollisionNode.addSolid(cogCollisionSphere)
                self.cogCol = suit.attachNewNode(cogCollisionNode)

                
            else: # Should be just pencil pusher.
                cogCollisionSphere = CollisionBox( (0,0,6), 1, 0.5, 5)
                cogCollisionSphere.setTangible(1)
                name = 'cogBox'
                cogBoxName = self.uniqueName(name)
                cogCollisionNode = CollisionNode('cogCollision')
                cogCollisionNode.addSolid(cogCollisionSphere)
                self.cogCol = suit.attachNewNode(cogCollisionNode)


            cogHurtCapsule = CollisionCapsule(0, 10, 0, 0, 20, 0, 5)
            #collPlane = CollisionCapsule(0, 10, 0, 0, 20, 0, 5) 
            # we're going to use a capsule to act as the view of the cog. Once touched, run a function that gets the Toon's speed.
            # If the toon's speed is higher than 1, subtract jellybeans.


        # Let the player see the toon. 
        playerToon = base.localAvatar
        playerToon.reparentTo(render)
        self.__placeToon(self.localAvId)
        playerToon.setSpeed(0, 0)
        base.localAvatar.attachCamera()
    
        # Set up the collisions that we'll need to end the game.
        toonCollisionSphere = CollisionSphere(0, 2.5, 2.5, 0.5)
        toonCollisionSphere.setTangible(0)
        toonCollisionNode = CollisionNode('toonCollision')
        toonCollisionNode.addSolid(toonCollisionSphere)
        self.toonCol = playerToon.attachNewNode(toonCollisionNode)
        #self.toonCol.show()
    

        toonSD = self.toonSDs[self.localAvId]
        toonSD.enter()
        toonSD.fsm.request('init') # Setting the toon's state to normal so they are just standing still.
        
        # Stopping the player from any input for now.
        self.stopGameWalk()

        # Start the music, we need the baller music while infiltrating Cashbot HQ.
        base.playMusic(self.music, looping = 1, volume = 0.7 )


    def offstage(self):
        '''Welp, now that it's time to start leaving, hide everything! No one needs to know this game existed.'''
        self.notify.debug('offstage')
        DistributedMinigame.offstage(self)
        self.room.hide()
        self.elevator.hide()
        self.consoleRoom.hide()
        self.console.hide()
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
        self.__startRewardCountdown()
        #self.__startCogRotations()
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
        self.accept('arrow_up', self.keyPressed)
        self.accept('arrow_right', self.keyPressed)
        self.accept('arrow_left', self.keyPressed)
        self.accept('arrow_down', self.keyPressed)

        self.accept('arrow_up-up', self.keyReleased)
        self.accept('arrow_right-up', self.keyReleased)
        self.accept('arrow_left-up', self.keyReleased)
        self.accept('arrow_down-up', self.keyReleased)

        chosenTime = self.randomNumGen.randint(5, WTGG.GameTime / 2)
        print(WTGG.GameTime - chosenTime)

        taskMgr.doMethodLater(chosenTime-1, self.playWarning, 'rotateCog')
        taskMgr.doMethodLater(chosenTime, self.rotateCogTowardsPlayer, 'rotateCogPlayer')
        taskMgr.doMethodLater(chosenTime+5, self.rotateCogTowardsDefault, 'rotateCogDefault')

        self.walkStateData.fsm.request('walking')

    def keyPressed(self):
        'Basically if you use any of the movement keys, the cog will know.'
        self.toonMoving = True
        #print("The player moved.")
    
    def keyReleased(self):
        'Basically if you use any of the movement keys, the cog will know.'
        self.toonMoving = False
        #print("The player has stopped moving.")

    def exitPlay(self):
        self.walkStateData.exit()
        pass

    def enterCleanup(self):
        self.__killRewardCountdown()
        if hasattr(self, 'jarIval'):
            self.jarIval.finish()
            del self.jarIval
        self.notify.debug('enterCleanup')
        for key in self.cogInfo:
            cogThief = self.cogInfo[key]['suit']
            cogThief.cleanup()

    def exitCleanup(self):
        pass

    # This is where all my personally created (and some copied over from Cog Thief) functions start.

    def initCogInfo(self):
        for cogIndex in xrange(self.getNumCogs()):
            self.cogInfo[cogIndex] = {'pos': Point3( VBase3(0.75, 100, 0) ),
             'goal': CTGG.NoGoal,
             'goalId': CTGG.InvalidGoalId,
             'suit': None}

        return

    def __startRewardCountdown(self):
        taskMgr.add(self.__updateRewardCountdown, self.REWARD_COUNTDOWN_TASK)

    def __killRewardCountdown(self):
        taskMgr.remove(self.REWARD_COUNTDOWN_TASK)

    def __updateRewardCountdown(self, task):
        '''Updates the jellybean jar depending on what time it is.''' 
        if self.rewardPanel['text'] == '0':
            self.gameOver()
            self.sendUpdate('changeStatusToLoss')
        else:
            timeElapsed = self.getCurrentGameTime()
            if self.rewardPanel['text'] != str(int(WTGG.GameTime - timeElapsed)):
                self.rewardPanel['text'] = str(int(WTGG.GameTime - timeElapsed))
                s = self.rewardPanel.getScale()
                self.jarIval = Parallel(Sequence(self.rewardPanel.scaleInterval(0.15, s * 3.0 / 4.0, blendType='easeOut'), self.rewardPanel.scaleInterval(0.15, s, blendType='easeIn')), SoundInterval(self.sndRewardTick), name='cogThiefGameRewardJarThrob')
                self.jarIval.start()
        return Task.again

    def rotateCogTowardsPlayer(self, Task):
        suit = self.cogInfo[0]['suit']
        suitBody = self.cogInfo[0]['suit'].suit 

        initialBoxRange = 10

        for i in range(20):
            cogCollisionBox = CollisionBox( (0,initialBoxRange,5), 7, 10, 5)
            initialBoxRange += 5
            cogCollisionBox.setTangible(0)
            name = 'cogBox'
            cogBoxName = self.uniqueName(name)
            cogCollisionNode = CollisionNode(cogBoxName)
            cogCollisionNode.addSolid(cogCollisionBox)
            self.cogCol = suitBody.attachNewNode(cogCollisionNode)
            self.cogCol.show()
            handler = CollisionHandlerEvent()
            handler.setInPattern('cogHit-%fn')
            base.cTrav.addCollider(self.cogCol, handler)
            self.accept('cogHit-' + cogBoxName, self.handleEnterBox)

        suit.rotateCogTowardToon()
        suit.CogLookingBack = True
        return Task.done
    
    def handleEnterBox(self, colEntry):
        if self.toonMoving:
            toon = self.localAvId
            self.__placeToon(self.localAvId)
    
    def playWarning(self, Task):
        self.cogWarning.play()
        return Task.done
    
    def rotateCogTowardsDefault(self, Task):
        suit = self.cogInfo[0]['suit']
        suitBody = self.cogInfo[0]['suit'].suit
        self.cogCol.removeNode()
        suit.rotateCogBackward()
        suit.CogLookingBack = False
        return Task.done
            
    def loadCogs(self): # I listed these cogs from the top of the ladder to the bottom.
        suitTypes = [
           'tbc', # The big cheese
           'le', # Legal Eagle
           'ls', # loan Shark
           'nc', # Number Cruncher
           'ms', # Mover & Shaker
           'mm', # Micromanager
           'p' # Pencil Pusher
            ] 
        for suitIndex in xrange(self.getNumCogs()):
            st = self.randomNumGen.choice(suitTypes)
            suit = Watcher.Watcher(st, self)
            self.cogInfo[suitIndex]['suit'] = suit

    def getNumCogs(self):
        '''We just want one cog. Maybe potentially get more at some point? We'll see.'''
        return 1

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

    def handleEnterBarrel(self, colEntry):
        # sends a message to the AI telling them "HEY, we won the game! Give us more jellybeans!"
        self.consoleActivating.play()
        self.gameWon = True
        self.showResults()
        self.gameOver()
        self.sendUpdate('changeStatusToWin')
    
    def handleEnterCog(self, colEntry):
        '''sends a message to the AI to reduce the amount of jellybeans and the jellybean jar reflects this change.
        Now an unused function. '''
        print("Cog has been collided with")

        #self.jellybeansToTake += 5
        #s = self.rewardPanel.getScale()
        #self.jarIval = Parallel(Sequence(self.rewardPanel.scaleInterval(0.15, s * 3.0 / 4.0, blendType='easeOut'), self.rewardPanel.scaleInterval(0.15, s, blendType='easeIn')), SoundInterval(self.sndRewardTick), name='cogThiefGameRewardJarThrob')
        #self.jarIval.start()
        #self.sendUpdate('reduceJellybeans', [5])
    
    def __gameTimerExpired(self):
        self.notify.debug('game timer expired')
        self.showResults()
        self.gameOver()

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

        textTrack = Sequence(Func(perfectText.reparentTo, aspect2d), Parallel(LerpScaleInterval(perfectText, duration=0.5, scale=0.3, startScale=0.0), LerpFunctionInterval(fadeFunc, fromData=0.0, toData=1.0, duration=0.5)), Wait(2.0), Parallel(LerpScaleInterval(perfectText, duration=0.5, scale=1.0), LerpFunctionInterval(fadeFunc, fromData=1.0, toData=0.0, duration=0.5, blendType='easeIn')), Func(destroyText), WaitInterval(0.5))

        self.resultIval = Parallel(textTrack)
        self.resultIval.start()
            
    
    def __genText(self, text):
        self.__textGen.setText(text)
        return self.__textGen.generate()


