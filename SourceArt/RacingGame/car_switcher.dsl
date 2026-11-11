; BP_RGC_CarSwitcher event graph (written with BlueprintTools.write_graph_dsl).
; Keys I/O/P/U/Y/T (or setting RequestedCar to 1..6) swaps the player's car for the Bee/Ant/Spider/Snail/Scorpion/Beetle racer at the
; same spot, keeping heading and speed. The old car is moved away with collision off before it is destroyed,
; so the new car never overlaps it (overlapping bodies flung the new car).
; Its OnDestroyed bindings are cleared first: otherwise BP_VehicleAdvPlayerController respawns a car at the
; PlayerStart, that spawn fails on collision and it then possesses the dead actor (PIE Blueprint Runtime Errors).
(event EventTick (DeltaSeconds)
  (bind pc (Game|GetPlayerController 0))
  (bind old (Pawn|GetControlledPawn :self pc))
  (Utilities|IsValid old
    (:"Is Valid"
      (bind loc (Transformation|GetActorLocation :self old))
      (bind rot (Transformation|GetActorRotation :self old))
      (bind xf (Math|Transform|MakeTransform
                 :Location (+ loc (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 60.0))
                 :Rotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw (.yaw rot))))
      (if (or (Game|Player|WasInputKeyJustPressed :self pc :Key "I") (== (Variables|Default|GetRequestedCar) 1))
  (Variables|Default|SetRequestedCar 0)
  (bind c1 (Utilities|Casting|CastToBP_RGC_BeeRacer :Object old
    (:CastFailed
      (Variables|Default|SetSavedXf xf)
      (Variables|Default|SetSavedVel (Transformation|GetVelocity :self old))
      (Collision|SetActorEnableCollision :self old :bNewActorEnableCollision false)
      (Transformation|SetActorLocation :self old :NewLocation (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z -100000.0) :bSweep false :bTeleport true)
      (Game|UnbindallEventsfromOnDestroyed :self old)
      (Actor|DestroyActor :self old)
      (bind n1 (Game|SpawnActorfromClass :Class "/Game/RacingGame/Vehicles/BeeRacer/BP_RGC_BeeRacer.BP_RGC_BeeRacer_C"
                 :SpawnTransform (Variables|Default|GetSavedXf) :CollisionHandlingOverride "AlwaysSpawn"))
      (Pawn|Possess :self pc :InPawn n1)
      (bind p1 (Actor|GetComponentbyClass :self n1 :ComponentClass "/Script/Engine.SkeletalMeshComponent"))
      (Physics|SetPhysicsLinearVelocity :self p1 :NewVel (Variables|Default|GetSavedVel)))))
(elif (or (Game|Player|WasInputKeyJustPressed :self pc :Key "O") (== (Variables|Default|GetRequestedCar) 2))
  (Variables|Default|SetRequestedCar 0)
  (bind c2 (Utilities|Casting|CastToBP_RGC_AntRacer :Object old
    (:CastFailed
      (Variables|Default|SetSavedXf xf)
      (Variables|Default|SetSavedVel (Transformation|GetVelocity :self old))
      (Collision|SetActorEnableCollision :self old :bNewActorEnableCollision false)
      (Transformation|SetActorLocation :self old :NewLocation (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z -100000.0) :bSweep false :bTeleport true)
      (Game|UnbindallEventsfromOnDestroyed :self old)
      (Actor|DestroyActor :self old)
      (bind n2 (Game|SpawnActorfromClass :Class "/Game/RacingGame/Vehicles/AntRacer/BP_RGC_AntRacer.BP_RGC_AntRacer_C"
                 :SpawnTransform (Variables|Default|GetSavedXf) :CollisionHandlingOverride "AlwaysSpawn"))
      (Pawn|Possess :self pc :InPawn n2)
      (bind p2 (Actor|GetComponentbyClass :self n2 :ComponentClass "/Script/Engine.SkeletalMeshComponent"))
      (Physics|SetPhysicsLinearVelocity :self p2 :NewVel (Variables|Default|GetSavedVel)))))
(elif (or (Game|Player|WasInputKeyJustPressed :self pc :Key "P") (== (Variables|Default|GetRequestedCar) 3))
  (Variables|Default|SetRequestedCar 0)
  (bind c3 (Utilities|Casting|CastToBP_RGC_SpiderRacer :Object old
    (:CastFailed
      (Variables|Default|SetSavedXf xf)
      (Variables|Default|SetSavedVel (Transformation|GetVelocity :self old))
      (Collision|SetActorEnableCollision :self old :bNewActorEnableCollision false)
      (Transformation|SetActorLocation :self old :NewLocation (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z -100000.0) :bSweep false :bTeleport true)
      (Game|UnbindallEventsfromOnDestroyed :self old)
      (Actor|DestroyActor :self old)
      (bind n3 (Game|SpawnActorfromClass :Class "/Game/RacingGame/Vehicles/SpiderRacer/BP_RGC_SpiderRacer.BP_RGC_SpiderRacer_C"
                 :SpawnTransform (Variables|Default|GetSavedXf) :CollisionHandlingOverride "AlwaysSpawn"))
      (Pawn|Possess :self pc :InPawn n3)
      (bind p3 (Actor|GetComponentbyClass :self n3 :ComponentClass "/Script/Engine.SkeletalMeshComponent"))
      (Physics|SetPhysicsLinearVelocity :self p3 :NewVel (Variables|Default|GetSavedVel)))))
(elif (or (Game|Player|WasInputKeyJustPressed :self pc :Key "U") (== (Variables|Default|GetRequestedCar) 4))
  (Variables|Default|SetRequestedCar 0)
  (bind c4 (Utilities|Casting|CastToBP_RGC_SnailRacer :Object old
    (:CastFailed
      (Variables|Default|SetSavedXf xf)
      (Variables|Default|SetSavedVel (Transformation|GetVelocity :self old))
      (Collision|SetActorEnableCollision :self old :bNewActorEnableCollision false)
      (Transformation|SetActorLocation :self old :NewLocation (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z -100000.0) :bSweep false :bTeleport true)
      (Game|UnbindallEventsfromOnDestroyed :self old)
      (Actor|DestroyActor :self old)
      (bind n4 (Game|SpawnActorfromClass :Class "/Game/RacingGame/Vehicles/SnailRacer/BP_RGC_SnailRacer.BP_RGC_SnailRacer_C"
                 :SpawnTransform (Variables|Default|GetSavedXf) :CollisionHandlingOverride "AlwaysSpawn"))
      (Pawn|Possess :self pc :InPawn n4)
      (bind p4 (Actor|GetComponentbyClass :self n4 :ComponentClass "/Script/Engine.SkeletalMeshComponent"))
      (Physics|SetPhysicsLinearVelocity :self p4 :NewVel (Variables|Default|GetSavedVel)))))
(elif (or (Game|Player|WasInputKeyJustPressed :self pc :Key "Y") (== (Variables|Default|GetRequestedCar) 5))
  (Variables|Default|SetRequestedCar 0)
  (bind c5 (Utilities|Casting|CastToBP_RGC_ScorpionRacer :Object old
    (:CastFailed
      (Variables|Default|SetSavedXf xf)
      (Variables|Default|SetSavedVel (Transformation|GetVelocity :self old))
      (Collision|SetActorEnableCollision :self old :bNewActorEnableCollision false)
      (Transformation|SetActorLocation :self old :NewLocation (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z -100000.0) :bSweep false :bTeleport true)
      (Game|UnbindallEventsfromOnDestroyed :self old)
      (Actor|DestroyActor :self old)
      (bind n5 (Game|SpawnActorfromClass :Class "/Game/RacingGame/Vehicles/ScorpionRacer/BP_RGC_ScorpionRacer.BP_RGC_ScorpionRacer_C"
                 :SpawnTransform (Variables|Default|GetSavedXf) :CollisionHandlingOverride "AlwaysSpawn"))
      (Pawn|Possess :self pc :InPawn n5)
      (bind p5 (Actor|GetComponentbyClass :self n5 :ComponentClass "/Script/Engine.SkeletalMeshComponent"))
      (Physics|SetPhysicsLinearVelocity :self p5 :NewVel (Variables|Default|GetSavedVel)))))
(elif (or (Game|Player|WasInputKeyJustPressed :self pc :Key "T") (== (Variables|Default|GetRequestedCar) 6))
  (Variables|Default|SetRequestedCar 0)
  (bind c6 (Utilities|Casting|CastToBP_RGC_BeetleRacer :Object old
    (:CastFailed
      (Variables|Default|SetSavedXf xf)
      (Variables|Default|SetSavedVel (Transformation|GetVelocity :self old))
      (Collision|SetActorEnableCollision :self old :bNewActorEnableCollision false)
      (Transformation|SetActorLocation :self old :NewLocation (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z -100000.0) :bSweep false :bTeleport true)
      (Game|UnbindallEventsfromOnDestroyed :self old)
      (Actor|DestroyActor :self old)
      (bind n6 (Game|SpawnActorfromClass :Class "/Game/RacingGame/Vehicles/BeetleRacer/BP_RGC_BeetleRacer.BP_RGC_BeetleRacer_C"
                 :SpawnTransform (Variables|Default|GetSavedXf) :CollisionHandlingOverride "AlwaysSpawn"))
      (Pawn|Possess :self pc :InPawn n6)
      (bind p6 (Actor|GetComponentbyClass :self n6 :ComponentClass "/Script/Engine.SkeletalMeshComponent"))
      (Physics|SetPhysicsLinearVelocity :self p6 :NewVel (Variables|Default|GetSavedVel))))))))))))
    (:"Is Not Valid")))
