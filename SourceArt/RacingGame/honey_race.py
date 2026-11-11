"""Garden Grand Prix: wrecked cars respawn on the track where they crashed (2026-11-01).

BPC_HoneyStatus (BugBattle damage) wrecks a car after enough ram damage and normally respawns it at a random
PlayerStart after ~8 s. On Lvl_GardenGrandPrix that put racers back on the start grid. These graphs keep the arena
behaviour unchanged and, on the race level only, respawn at the nearest RaceManager track point (facing the race
direction) after a short delay. Originals: Saved/RG_backup_honey/*.dsl (+ the .uasset).
Writes honey_finishrespawn.dsl, honey_respawnvehicle.dsl, honey_racerespawnpoint.dsl (+ Saved/RacingGame/*.txt).
"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
SAVED = os.path.join(HERE, "..", "..", "Saved", "RacingGame")
RM_C = "/Game/RacingGame/Gameplay/BP_RG_RaceManager.BP_RG_RaceManager_C"
RACE_RESPAWN_DELAY = 0.6        # hidden time after the wreck (the wreck itself already lasts WreckDestroyDelay >= 1.2 s)
IS_RACE = '(Utilities|String|Equal,CaseInsensitive(String) (Game|GetCurrentLevelName true) "Lvl_GardenGrandPrix")'

FINISH = """(fn FinishRespawn ()
  (bind _returnvalue (Components|GetOwner))
  (bind _vehiclemesh (Variables|Default|GetVehicleMesh))
  (if %(race)s
    (CallFunction|RaceRespawnPoint)
    (else
      (bind _outactors (Actor|GetAllActorsOfClass "/Script/Engine.PlayerStart"))
      (if (> (Utilities|Array|Length _outactors) 0)
        (Variables|Default|SetRespawnTransform (Transformation|GetActorTransform (Utilities|Array|Get(acopy) _outactors (Math|Random|RandomIntegerInRange 0 (- (Utilities|Array|Length _outactors) 1))))))))
  (Variables|Health|SetDamageTaken 0.0)
  (Variables|Default|SetHitGraceEnd (+ (Utilities|Time|GetGameTimeInSeconds) 2.0))
  (bind rxf (Variables|Default|GetRespawnTransform))
  (Transformation|SetActorLocationAndRotation :self _returnvalue :NewLocation (+ (.location rxf) (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 80.0)) :NewRotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw (.yaw (.rotation rxf))) :bSweep false :bTeleport true)
  (Physics|SetSimulatePhysics _vehiclemesh true)
  (CallFunction|FixWheelBodies)
  (Collision|SetActorEnableCollision _returnvalue true)
  (Physics|SetPhysicsLinearVelocity _vehiclemesh (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 0.0))
  (Physics|SetPhysicsAngularVelocityInDegrees _vehiclemesh (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 0.0))
  (Physics|SetLinearDamping _vehiclemesh (Variables|Default|GetOrigLinearDamping))
  (Rendering|SetActorHiddenInGame _returnvalue false)
  (Utilities|Time|SetTimerbyFunctionName self "ClearWrecked" 1.5))
""" % dict(race=IS_RACE)

RESPAWN = """(fn RespawnVehicle ()
  (bind _returnvalue (Components|GetOwner))
  (bind _vehiclemesh (Variables|Default|GetVehicleMesh))
  (if (Networking|HasAuthority _returnvalue)
    (Rendering|SetActorHiddenInGame _returnvalue true)
    (Collision|SetActorEnableCollision _returnvalue false)
    (Physics|SetPhysicsLinearVelocity _vehiclemesh (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 0.0))
    (Physics|SetPhysicsAngularVelocityInDegrees _vehiclemesh (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 0.0))
    (Physics|SetSimulatePhysics _vehiclemesh false)
    (Variables|Default|SetImmobilizeEndTime 0.0)
    (Variables|Default|SetSlowEndTime 0.0)
    (Variables|Default|SetImmobilized false)
    (Variables|Default|SetSlowed false)
    (if %(race)s
      (Utilities|Time|SetTimerbyFunctionName self "FinishRespawn" %(delay).2f)
      (else
        (Utilities|Time|SetTimerbyFunctionName self "FinishRespawn" (select (Pawn|IsPlayerControlled (Variables|Default|GetOwnerPawn)) (Math|Float|Max(Float) 0.8 (- 8.0 (Math|Float|Max(Float) (Variables|Default|GetWreckDestroyDelay) 1.2))) 4.0))))))
""" % dict(race=IS_RACE, delay=RACE_RESPAWN_DELAY)

POINT = """(fn RaceRespawnPoint ()
  (bind wl (.location (Variables|Default|GetRespawnTransform)))
  (bind rm (Utilities|Casting|CastToBP_RG_RaceManager (Actor|GetActorOfClass "%(rm)s"))
    (:then
      (bind pts (Class|BPRGRaceManager|GetTrackPts rm))
      (Variables|Default|SetRaceBestD 1000000000000000.0)
      (for i (range (Utilities|Array|Length pts))
        (bind d (Math|Vector|Distance2DSquared(Vector) wl (Utilities|Array|Get(acopy) pts i)))
        (if (< d (Variables|Default|GetRaceBestD))
          (Variables|Default|SetRaceBestD d)
          (Variables|Default|SetRaceBestI i)))
      (bind bi (Variables|Default|GetRaceBestI))
      (Variables|Default|SetRespawnTransform (Math|Transform|MakeTransform :Location (Utilities|Array|Get(acopy) pts bi) :Rotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw (Utilities|Array|Get(acopy) (Class|BPRGRaceManager|GetTrackYaw rm) bi)))))
    (:CastFailed)))
""" % dict(rm=RM_C)

# race-only crash rule, called first in HandleOwnerHit (returns Handled = true on the race level so the arena rules
# are skipped): another car closing at >= RACE_WRECK_SPEED wrecks this car at once; slower bumps and walls do nothing
RACE_WRECK_SPEED = 1500.0       # cm/s closing speed (54 km/h)
RACEHIT = """(fn RaceHit (OtherActor)
  (if %(race)s
    (bind ov (Utilities|Casting|CastToWheeledVehiclePawn OtherActor)
      (:then
        (bind me (Components|GetOwner))
        (bind dir (Math|Vector|Normalize (- (Transformation|GetActorLocation :self me) (Transformation|GetActorLocation :self OtherActor))))
        (bind closing (Math|Vector|DotProduct (- (Transformation|GetVelocity OtherActor) (Transformation|GetVelocity me)) dir))
        (if (and (>= closing %(spd).1f) (not (Variables|Default|GetWrecked)))
          (CallFunction|BBApplyDamage :Amount 1000.0 :Attacker OtherActor :UseGrace false))
        (return true))
      (:CastFailed
        (return true))))
  (return false))
""" % dict(race=IS_RACE, spd=RACE_WRECK_SPEED)

for nm, code in (("honey_racehit", RACEHIT), ("honey_finishrespawn", FINISH), ("honey_respawnvehicle", RESPAWN), ("honey_racerespawnpoint", POINT)):
    open(os.path.join(HERE, nm + ".dsl"), "w", encoding="utf-8").write(code)
    open(os.path.join(SAVED, nm + ".txt"), "w", encoding="utf-8").write(code)
print("ok")
