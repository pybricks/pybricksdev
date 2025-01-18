# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Fix crash when running `pybricksdev run ble -` (bug introduced in alpha.49).

## [1.0.0-alpha.52] - 2024-11-29

### Added
- Added support for Python 3.13.

## [1.0.0-alpha.51] - 2024-11-01

### Added
- Added `pybricksdev oad info` command.
- Added `pybricksdev oad flash` command.

### Fixed
- Fixed EV3 firmware flashing on USB 3.0 systems.

## [1.0.0-alpha.50] - 2024-07-01

### Changed
- Improved `SyntaxError` handling in `lwp3 repl` command.
- Minimum Python version changed to 3.10.

### Fixed
- Fixed `PortID` exception when running `lwp3 repl` command.

## [1.0.0-alpha.49] - 2024-06-30

### Changed
- Use relative paths when compiling multi-file projects.
- Better error message when hitting Python bug when compiling multi-file projects.

### Fixed
- Fixed `pybricksdev` BLE commands not working on Windows when `pythoncom`
  package is present in environment.

## [1.0.0-alpha.48] - 2024-05-04

### Changed
- Updated `hidapi` dependency to v0.14.0.

### Fixed
- Fixed installing on Windows due to failed `hidapi` installation.

## [1.0.0-alpha.47] - 2024-05-04

### Changed
- Allow hostname in `pybricksdev run ssh --name=...`.
- Updated `bleak` dependency to v0.22.0.
- Support Python up to 3.12.

### Fixed
- Fixed bug in udev rules.

## [1.0.0-alpha.46] - 2023-05-01

### Added
- Added `PybricksHub.download_user_program()` method ([support#284]).
- Added support for flashing EV3 firmware.
- Added support for MPY ABI v6.1.

[support#284]: https://github.com/pybricks/support/issues/284

## [1.0.0-alpha.45] - 2023-04-21

### Added
- Added `PybricksHub.stdout_observable` property ([support#1038]).

### Fixed
- Fixed endline in `PybricksHub.write_line()`.

[support#1038]: https://github.com/pybricks/support/issues/1038

## [1.0.0-alpha.44] - 2023-04-20

### Fixed
- Restored `PybricksHub.output` attribute ([support#1037]).

[support#1037]: https://github.com/pybricks/support/issues/1037

## [1.0.0-alpha.43] - 2023-04-19

### Added
- Added support for Pybricks Profile v1.3.0.
- Added new `PybricksHub.write_string()` method.
- Added new `PybricksHub.write_line()` method.
- Added new `PybricksHub.read_line()` method.
- Added new `PybricksHub.start_user_program()` method.
- Added new `PybricksHub.stop_user_program()` method.

## [1.0.0-alpha.42] - 2023-04-12

### Fixed
- Fixed Bleak `FutureWarning` about using `BLEDevice.metadata`.

## [1.0.0-alpha.41] - 2023-03-26

### Fixed
- Fixed `pybricks.ble.find_device()` returning with `name is None` on Windows ([support#1010]).

[support#1010]: https://github.com/orgs/pybricks/discussions/1010

## [1.0.0-alpha.40] - 2023-03-22

### Changed
- Updated `bleak` dependency to v0.20.0.

## [1.0.0-alpha.39] - 2023-03-06

### Fixed
- Fixed Python 3.11 compatibility of vendored `dfu_upload` module ([support#973]).

[support#973]: https://github.com/pybricks/support/issues/973

## [1.0.0-alpha.38] - 2023-03-03

### Added
- Added `pybricksdev.connections.ConnectionState` enum class.
- Added `pybricksdev.connections.pybricks.PybricksHub.connection_state_observable` attribute.

### Fixed
- Fixed `pybricksdev.connections.pybricks.PybricksHub` disconnect state not reset after reconnect ([support#971]).

### Removed
- Removed `pybricksdev.connections.pybricks.PybricksHub.disconnect_observable` attribute.
- Removed `pybricksdev.connections.pybricks.PybricksHub.connected` attribute.


[support#971]: https://github.com/pybricks/support/issues/971

## [1.0.0-alpha.37] - 2023-02-27

### Added
- Added support for including precompiled .mpy libraries.

## [1.0.0-alpha.36] - 2023-02-18

### Changed
- Changed EV3 script runner to just copy the script instead of replicating
  the local directory structure on the brick.

## [1.0.0-alpha.35] - 2023-02-10

### Added
- Added support for Python 3.11.

## [1.0.0-alpha.34] - 2023-01-21

### Added
- Added `pybricksdev.ble.pybricks.Command.PBIO_PYBRICKS_COMMAND_REBOOT_TO_UPDATE_MODE`.
- Added support for Pybricks firmware metadata v2.1.0.
- Added support for flashing firmware to LEGO MINDSTORMS NXT bricks.

### Fixed
- Fixed reboot in update mode for Pybricks Profile >= 1.2.0 in `pybricksdev flash` CLI.

## [1.0.0-alpha.33] - 2022-11-06

### Changed
- Updated Bleak dependency to v0.19.4.

## [1.0.0-alpha.32] - 2022-10-14

### Added
- Added support for Pybricks Profile v1.2.0 (BLE).

## [1.0.0-alpha.31] - 2022-09-14

### Added
- Experimental support for relative and nested imports.
- Added support for `firmware.metadata.json` v2.0.0.

### Changed
- Move/renamed `pybricksdev.flash.create_firmware` to `pybricksdev.firmware.create_firmware_blob`.
- Changed return value of `pybricksdev.firmware.create_firmware_blob` to include license text.

### Fixed
- Fixed "object is not subscriptable" error in Python 3.8 in `firmware` module.

## [1.0.0-alpha.30] - 2022-08-26

### Added
- Added `fw_version` attribute to `pybricksdev.connections.pybricks.PybricksHub`.
- Experimental support for multi-file projects.

### Fixed
- Fixed running programs on hubs with firmware with MPY ABI v5.

## [1.0.0-alpha.29] - 2022-07-08

### Changed
- Changed ABI default value to v6 for running programs.

## [1.0.0-alpha.28] - 2022-07-04

## Added
- Added support for compiling to MPY ABI v6 (MicroPython v1.19+).

## Changed
- `abi` arg is now required in `compile.compile_file`.

## [1.0.0-alpha.27] - 2022-06-21

## Changed
- Changed dependency from `mpy-cross` to `mpy-cross-v5`.
- Increased wait time when waiting for user program to start in `PybricksHub.run()`.

### Fixed
- Fix syntax error on Python < 3.10 in `firmware` module.

## [1.0.0-alpha.26] - 2022-06-07

### Added
- Added typings for firmware metadata json structure.
  
### Changed
- ``main.py`` in ``firmware.zip`` is now optional.

### Removed
- Removed support for ``firmware.zip`` files with ``firmware.bin`` instead of
  ``firmware-base.bin``.

## [1.0.0-alpha.25] - 2022-03-17

### Added
- Added ``PybricksHub.race_disconnect()`` method.

### Changed
- Moved `EV3Connection` from `connections` to `connections.ev3dev`.
- Moved `REPLHub` from `connections` to `connections.lego`.
- Moved `PybricksHub` from `connections` to `connections.pybricks`.

### Fixed
- Fixed race condition with `pybricksdev run ble` not waiting for program to
  finish before disconnecting ([pybricksdev#28]).

[pybricksdev#28]: https://github.com/pybricks/pybricksdev/issues/28

## [1.0.0-alpha.24] - 2022-01-25

### Fixed
- Fixed regression causing crash when attempting to flash SPIKE firmware ([support#617]).

[support#617]: https://github.com/pybricks/support/issues/617

## [1.0.0-alpha.23] - 2022-01-17

### Fixed
- Fixed ``pybricksdev flash`` command with ``--name`` argument not connecting.

## [1.0.0-alpha.22] - 2022-01-17

### Added
- Added ``ble.lpw3.AdvertisementData`` class.
- Added ``ble.lpw3.BootloaderAdvertisementData`` class.

### Changed
- Moved ``Bootloader*`` to new ``ble.lwp3.bootloader`` module.
- ``pybricksdev flash`` will now discover hubs running official LEGO firmware
  or Pybricks firmware and reboot in bootloader mode automatically.

## [1.0.0-alpha.21] - 2022-01-12

### Changed
- Updated `bleak` dependency to v0.14.1.


## [1.0.0-alpha.20] - 2022-01-10

### Changed
- Updated `bleak` dependency to v0.14.0.

### Fixed
- Fixed Bluetooth Low Energy not working on macOS 12.


- Updated `bleak` dependency to v0.12.1.
## [1.0.0-alpha.19] - 2021-12-24

### Fixed
- Fixed incorrect metadata checksum for the firmware installer for SPIKE hubs.

## [1.0.0-alpha.18] - 2021-12-03

### Added
- Added support for Python 3.10.

### Fixed
- Fixed `tqdm` dependency version.
- Fixed being unable to set the name of SPIKE hubs.

## [1.0.0-alpha.17] - 2021-10-25

### Added
- Experimental firmware installation on SPIKE Prime and SPIKE Essential via
  usb. The command line commands are unchanged. If you try to install the
  firmware on SPIKE hubs, it will first look for a hub running the regular
  firmware. If it doesn't find any, it will proceed using DFU as before.

## Changed
- Firmware binaries for SPIKE hubs are no longer being customized with a main
  script and a changed checksum. Instead, it simply installs firmware.bin from
  the CI ZIP file.

## [1.0.0-alpha.16] - 2021-10-12

### Added
- Script runner for generic MicroPython boards via USB. This is mainly used for
  debugging.

## Fixed
- Visual Studio Code launcher settings to run a script via BLE.

## [1.0.0-alpha.15] - 2021-09-21

### Added
- Added `VOLUME` to `ble.lwp3.bytecodes.HubProperty` enum.
- Added SPIKE Essential hub device IDs.
- Added Luigi hub device ID.
- 
## Fixed
- Fixed BlueZ disconnecting when sending a command with `pybricksdev lwp3 repl`
  to a City hub.


## [1.0.0-alpha.14] - 2021-08-27

## Changed
- Changed udev rules to use `TAG+="uaccess"` instead of `MODE="0666"`.

## Fixed
- Fixed device not rebooting after `dfu restore`.

## [1.0.0-alpha.13] - 2021-08-06

### Fixed
- Fixed crash in CRC32 checksum.
- Fixed flashing with `dfu-util` not always working ([support#420]).

[support#420]: https://github.com/pybricks/support/issues/420

## [1.0.0-alpha.12] - 2021-08-04

### Changed
- Updated `bleak` dependency to v0.12.1.
- `run` and `compile` scripts now accept `-` as an argument to mean stdin.

### Removed
- Removed script command line args in `run` and `compile` commands. Only accepts
  file name now.

## [1.0.0-alpha.11] - 2021-07-05

### Added
- Added support for Pybricks Protocol v1.1.0.

### Fixed
- Fixed `pybricksdev ble run` not working with BOOST Move hub.

## [1.0.0-alpha.10] - 2021-06-27
### Added
- Support for Python 3.9.
- Short `-n` option for `--name` option in `pybricksdev run`.
- Option to set hub name when flashing firmware.
### Changed
- Update to Bleak v0.12.0.
- Change `pybricksdev run` to use `--wait`/`--no-wait` instead of `--wait=False`.
### Fixed
- Fix `pybricksdev lwp3 repl` can only connect to remote control.
- Fix Technic Large hub Bluetooth hub kind.

## [1.0.0-alpha.9] - 2021-05-27
## Added
- `pybricksdev.ble.lwp3.bytecodes` module.
- `pybricksdev.ble.lwp3.messages` module.
- `pybricksdev lwp3 repl` command line tool.
## Fixed
- Crash when running `pybricksdev dfu` without args on command line.

## [1.0.0-alpha.8] - 2021-05-18
## Added
- `pybricksdev.ble.lwp3` module.
- `pybricksdev.ble.nus` module.
- `pybricksdev.ble.pybricks` module.
## Changed
- Name parameter to `pybricksdev run ble` command is now optional.
## Fixed
- Connecting to BLE devices based on Bluetooth address.

## [1.0.0-alpha.7] - 2021-05-17
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

## 1.0.0-alpha.6
- Skipped for technical reasons.

## [1.0.0-alpha.5] - 2021-05-04
### Added
- REPL installer for SPIKE/MINDSTORMS hubs.
### Fixed
- Data logging to file.

## [1.0.0-alpha.4] - 2021-04-12
### Added
- Size check when restoring firmware via USB/DFU.
- Added `pybricksdev.tools.chunk()` function.
- Added basic command completion to `pybricksdev lwp3 repl`.
### Fixed
- Wait for some time to allow program output to be received before disconnecting
  in the `run` command.
- Fixed spelling of `INPUT` in `pybricksdev.ble.lwp3.messages`.
- Fixed `pybricksdev lwp3 repl` does not exit if device disconnects.

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



[Unreleased]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.52..HEAD
[1.0.0-alpha.52]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.51...v1.0.0-alpha.52
[1.0.0-alpha.51]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.50...v1.0.0-alpha.51
[1.0.0-alpha.50]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.49...v1.0.0-alpha.50
[1.0.0-alpha.49]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.48...v1.0.0-alpha.49
[1.0.0-alpha.48]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.47...v1.0.0-alpha.48
[1.0.0-alpha.47]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.46...v1.0.0-alpha.47
[1.0.0-alpha.46]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.45...v1.0.0-alpha.46
[1.0.0-alpha.45]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.44...v1.0.0-alpha.45
[1.0.0-alpha.44]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.43...v1.0.0-alpha.44
[1.0.0-alpha.43]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.42...v1.0.0-alpha.43
[1.0.0-alpha.42]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.41...v1.0.0-alpha.42
[1.0.0-alpha.41]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.40...v1.0.0-alpha.41
[1.0.0-alpha.40]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.39...v1.0.0-alpha.40
[1.0.0-alpha.39]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.38...v1.0.0-alpha.39
[1.0.0-alpha.38]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.37...v1.0.0-alpha.38
[1.0.0-alpha.37]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.36...v1.0.0-alpha.37
[1.0.0-alpha.36]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.35...v1.0.0-alpha.36
[1.0.0-alpha.35]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.34...v1.0.0-alpha.35
[1.0.0-alpha.34]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.33...v1.0.0-alpha.34
[1.0.0-alpha.33]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.32...v1.0.0-alpha.33
[1.0.0-alpha.32]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.31...v1.0.0-alpha.32
[1.0.0-alpha.31]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.30...v1.0.0-alpha.31
[1.0.0-alpha.30]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.29...v1.0.0-alpha.30
[1.0.0-alpha.29]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.28...v1.0.0-alpha.29
[1.0.0-alpha.28]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.27...v1.0.0-alpha.28
[1.0.0-alpha.27]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.26...v1.0.0-alpha.27
[1.0.0-alpha.26]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.25...v1.0.0-alpha.26
[1.0.0-alpha.25]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.24...v1.0.0-alpha.25
[1.0.0-alpha.24]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.23...v1.0.0-alpha.24
[1.0.0-alpha.23]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.22...v1.0.0-alpha.23
[1.0.0-alpha.22]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.21...v1.0.0-alpha.22
[1.0.0-alpha.21]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.20...v1.0.0-alpha.21
[1.0.0-alpha.20]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.19...v1.0.0-alpha.20
[1.0.0-alpha.19]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.18...v1.0.0-alpha.19
[1.0.0-alpha.18]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.17...v1.0.0-alpha.18
[1.0.0-alpha.17]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.16...v1.0.0-alpha.17
[1.0.0-alpha.16]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.15...v1.0.0-alpha.16
[1.0.0-alpha.15]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.14...v1.0.0-alpha.15
[1.0.0-alpha.14]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.13...v1.0.0-alpha.14
[1.0.0-alpha.13]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.12...v1.0.0-alpha.13
[1.0.0-alpha.12]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.11...v1.0.0-alpha.12
[1.0.0-alpha.11]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.10...v1.0.0-alpha.11
[1.0.0-alpha.10]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.9...v1.0.0-alpha.10
[1.0.0-alpha.9]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.8...v1.0.0-alpha.9
[1.0.0-alpha.8]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.7...v1.0.0-alpha.8
[1.0.0-alpha.7]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.5...v1.0.0-alpha.7
[1.0.0-alpha.5]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.4...v1.0.0-alpha.5
[1.0.0-alpha.4]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.3...v1.0.0-alpha.4
[1.0.0-alpha.3]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.2...v1.0.0-alpha.3
[1.0.0-alpha.2]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.1...v1.0.0-alpha.2
[1.0.0-alpha.1]: https://github.com/pybricks/pybricksdev/compare/v1.0.0-alpha.0...v1.0.0-alpha.1
