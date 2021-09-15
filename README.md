# ToontownMinigames
Toontown minigames I've created using Toontown School House.

Games to work on:

1. DistributedWatchingGame:

Barebones Version - 99% (I haven't gotten a chance to look at the bug as I finished the finalized edition so I will try to make time and then I'll upload a fix)

Finalized Version - Finished! The final product can be seen at https://www.reddit.com/r/toontownrewritten/comments/pnrbfc/i_recreated_ttrs_red_light_green_light_trolley/?ref=share&ref_source=link

2. ??? - Somewhat planning this for now (no promises), but I think it would be a cool idea if done right, especially in Toontown.

Things I've learned about since starting to work on this:
- Using the DC file to create AI functions that allow communication between the minigame and its AI server.
- Using the taskMgr to execute functions at certain times
- Inserting a new minigame into the Trolley chooser
- Sending updates to the AI to end the game
- loading, rotating, and placing models
- Using CollisionNodes to take in player collisions and executing functions based on those collisions.
- Using various types of Collision Solids including CollisionBoxes and CollisionSpheres
- Adding NPCs to the game
- Changing the WalkFSM states to prevent players from moving in certain situations.
- Utilizing LerpHprInterval and LerpPosInterval for game mechanics and game cutscenes, respectively.
