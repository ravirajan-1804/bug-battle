; BPC_RGC_Drift event graph (written with BlueprintTools.write_graph_dsl).
; 2026-10-17: drift and the 120 km/h speed cap were both removed on user request. The component is now empty
; (cars use their normal handling and top speed). Old drift + cap graph: Saved/drift_withdrift_backup.dsl.
(event EventBeginPlay)

(event EventTick (DeltaSeconds))
