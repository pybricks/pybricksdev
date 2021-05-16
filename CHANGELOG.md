# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
## Added
- Debug option to CLI interface.
## Changed
- Use standard Python logging for modules instead of per-object.
- Use progress bars when downloading program to hub.
## Removed
- Delay option in CLI `flash` command.
## Fixed
- Flashing firmware using BLE under conditions on Windows.
- `NotImplementedError` when compiling to .mpy in ipython kernel on Windows.

## [1.0.0-alpha.5] - 2021-05-04
### Added
- REPL installer for SPIKE/MINDSTORMS hubs.
### Fixed
- Data logging to file.

## [1.0.0-alpha.4] - 2021-04-12
### Added
- Size check when restoring firmware via USB/DFU.
### Fixed
- Wait for some time to allow program output to be received before disconnecting
  in the `run` command.

## [1.0.0-alpha.3] - 2021-04-09
### Changed
- Print BLE download progress after chunk is complete instead of before.
### Fixed
- Fix occasional bad checksum warning when running program via BLE.

## [1.0.0-alpha.2] - 2021-04-08
### Added
- Check Pybricks protocol version when connecting to Bluetooth Low Energy devices.
### Fixed
- Fix running programs via Bluetooth Low Energy.

## [1.0.0-alpha.1] - 2021-04-07
### Added
- This changelog.
### Fixed
- DFU flashing not working on Windows.
- Typo in `pip` arguments `README.md`.


[Unreleased]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.5..HEAD
[1.0.0-alpha.5]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.4...v1.0.0-alpha.5
[1.0.0-alpha.4]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.3...v1.0.0-alpha.4
[1.0.0-alpha.3]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.2...v1.0.0-alpha.3
[1.0.0-alpha.2]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.1...v1.0.0-alpha.2
[1.0.0-alpha.1]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.0...v1.0.0-alpha.1