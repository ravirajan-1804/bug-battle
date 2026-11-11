# Bug Battle

A vehicle-combat and racing game set in a miniature garden, built in Unreal Engine. Bug-themed cars fight in arenas and race a garden circuit. In development.

- **Engine:** Unreal Engine 5.8
- **Built with:** Blueprint, Chaos Vehicles, Python scripts for generating meshes, materials and levels
- **Project file:** `Battle.uproject`

## What's in this repo

| Folder | Contents |
| --- | --- |
| `Content/BugBattle` | Arena levels, bot AI components, HUD, meshes, materials, audio and effects |
| `Content/Abilities` | Vehicle powers: Bee Powers, Honey Bomb, Royal Bee Swarm |
| `Content/AntCar`, `Content/SpiderCar` | Bug cars with their Blueprints, input and abilities |
| `Content/RacingGame` | Garden Grand Prix racing mode: track, gameplay, UI and vehicles |
| `Content/Vehicles`, `Content/VehicleTemplate` | Unreal vehicle template content the project builds on |
| `SourceArt` | Python scripts, plans and notes used to generate the art, plus sound effects |
| `Config` | Project settings |

## Levels

- **Arenas:** `Lvl_GardenArena`, `Lvl_Garden2`, `Lvl_HiveArena`, `Lvl_MushroomGlade`, `Lvl_PicnicArena` in `Content/BugBattle/Maps`
- **Racing:** `Lvl_GardenGrandPrix` in `Content/RacingGame/Maps`; see `SourceArt/RacingGame/README.md` for the track notes

## Open the project

1. Install Unreal Engine 5.8 and [Git LFS](https://git-lfs.com).
2. Clone the repo. The `.uasset`, `.umap` and `.wav` files are stored with Git LFS.
3. Open `Battle.uproject`.

The exported `.obj` and `.fbx` source meshes are not in the repo; they are already imported into `Content/`.

## Author

Ravi Rajan · [Portfolio](https://ravi-rajan-portfolio.vercel.app)
