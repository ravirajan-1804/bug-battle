# Spider Car power animation (from SpiderCar_Abilities.blend)

The Spider Car powers in game use the user's Blender animation `SpiderCar_Abilities.blend` (Claude scratch workspace,
next to `SpiderCar.blend`). Nothing is re-modelled or replaced with particles: the meshes are the .blend objects and
the timing is the .blend keyframes, sampled per frame.

Not used from the .blend (by request or because they are not power effects): every explosion (`FX_Explosion_*`, venom
blast radius, exploding enemy parts), the enemy cars, arena, cameras, labels/HP bars, the missiles, and the spider
leg poses (the in-game car is the SpiderRacer body mesh, which has no legs).

## Rebuild

1. `E:/blender.exe -b SpiderCar_Abilities.blend --python export_spidercar_abilities.py -- D:/Game/SourceArt/SpiderCar`
   writes `fbx/SM_SpiderCar_*.fbx`, `SpiderCar_Abilities_Curves.csv` and `SpiderCar_Abilities_Export.json`.
2. Import each FBX with unreal-mcp `StaticMeshTools.import_file` into `/Game/SpiderCar/Abilities/Meshes`
   (no materials, combine meshes), then `remove_collisions`.
3. Paste `build_spidercar_materials.py` into `ProgrammaticToolset.execute_tool_script` to rebuild
   `/Game/SpiderCar/Abilities/Materials`, then assign slots (WEB_SILK -> M_SpiderCar_Silk, WEB_SILK_FILM ->
   MI_SpiderCar_WebFilm, WEB_COCOON_FILM -> MI_SpiderCar_CocoonFilm, FX_SILK_FLASH -> MI_SpiderCar_SilkFlash,
   FX_VENOM_GREEN -> MI_SpiderCar_VenomGreen, FX_DASH_STREAK -> MI_SpiderCar_DashStreak, FX_SPARKS -> M_SpiderCar_Sparks,
   FX_SMOKE -> M_SpiderCar_Smoke, SPIDER_* -> MI_SpiderCar_Fang_*). Spark meshes get +-300 cm bounds extension (WPO).
4. `CurveTableTools.import_file` the CSV as `/Game/SpiderCar/Abilities/Data/CT_SpiderCar_Abilities` (RCIM_Linear).

## Runtime

| Power | Blueprint | .blend assets used |
|---|---|---|
| Web Shot | `BP_WebShot` (projectile + tether), `BPC_SpiderPowers.SpFxShot` (muzzle flash), `BP_WebWrap` (net, tether fade, impact sparks; ground web on a miss) | WEB_Shot_Projectile, WEB_Shot_Tether, FX_WebShot_Muzzle_Flash, WEB_Trap_Net, FX_WebShot_Impact_Silk |
| Venom Bite | `SpFxBite` (fangs, venom flash, droplets), `BP_SpiderCar_VenomFX` (vein overlay, engine-jam smoke + sparks) | SPIDERCAR_Venom_Fang_L/R, FX_Venom_Bite_Flash, FX_Venom_Droplets, ENEMY_PAINT veins, FX_Engine_Jam_Smoke/Sparks |
| Web Storm | `SpFxStorm` (field, spinneret flash), `BP_WebWrap` (nets on trapped cars, entangled projectiles) | WEB_Storm_Field, FX_Storm_Spinneret_Flash, WEB_Trap_Net, WEB_Entangle_Wrap, FX_Storm_Catch |
| Web Cocoon | `SpFxCocoon` | WEB_Cocoon_Shield, FX_Cocoon_Spin_Flash, FX_Cocoon_Break_Fragments |
| Dash | `SpFxDash` | FX_Dash_Speed_Streaks, FX_Dash_Collision_Sparks |

Gameplay (timings, damage, stuck/poison, cooldowns, replication) is unchanged; each effect plays its .blend intro
curve from the gameplay event, holds for the gameplay duration, then plays its .blend outro curve.
Car-attached parts are fitted from the .blend spider bounds to `SM_RGC_SpiderRacer_Body`; the fangs sit at the old
visible fang sockets (226, +-34, 40). The storm field is scaled to the gameplay radius (15 m; 9.5 m in the .blend).
