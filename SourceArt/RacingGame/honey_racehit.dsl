(fn RaceHit (OtherActor)
  (if (Utilities|String|Equal,CaseInsensitive(String) (Game|GetCurrentLevelName true) "Lvl_GardenGrandPrix")
    (bind ov (Utilities|Casting|CastToWheeledVehiclePawn OtherActor)
      (:then
        (bind me (Components|GetOwner))
        (bind dir (Math|Vector|Normalize (- (Transformation|GetActorLocation :self me) (Transformation|GetActorLocation :self OtherActor))))
        (bind closing (Math|Vector|DotProduct (- (Transformation|GetVelocity OtherActor) (Transformation|GetVelocity me)) dir))
        (if (and (>= closing 1500.0) (not (Variables|Default|GetWrecked)))
          (CallFunction|BBApplyDamage :Amount 1000.0 :Attacker OtherActor :UseGrace false))
        (return true))
      (:CastFailed
        (return true))))
  (return false))
