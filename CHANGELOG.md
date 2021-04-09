# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
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


[Unreleased]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.2..HEAD
[1.0.0-alpha.2]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.1...v1.0.0-alpha.2
[1.0.0-alpha.1]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.0...v1.0.0-alpha.1