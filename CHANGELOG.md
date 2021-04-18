# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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


[Unreleased]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.4..HEAD
[1.0.0-alpha.3]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.3...v1.0.0-alpha.4
[1.0.0-alpha.3]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.2...v1.0.0-alpha.3
[1.0.0-alpha.2]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.1...v1.0.0-alpha.2
[1.0.0-alpha.1]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.0...v1.0.0-alpha.1