# TinyCal 节假日更新脚本 (TinyCal Holiday Updater)

## 项目简介

本项目是一个 Python 脚本，用于更新 macOS 平台上的 [TinyCal (小历) App](https://apps.apple.com/cn/app/%E5%B0%8F%E5%8E%86-%E5%B0%8F%E8%80%8C%E7%BE%8E%E7%9A%84%E6%97%A5%E5%8E%86/id1114272557?mt=12) 的中国大陆节假日和补班日数据。

由于 TinyCal 应用官方的节假日数据有时更新不够及时，可能会导致日历中的假期显示不准确。本脚本旨在通过从权威数据源获取最新的节假日信息，并自动更新 TinyCal 的本地配置文件，来解决这个问题。

## 功能特性

* **自动获取最新数据**：从 [NateScarlet/holiday-cn](https://github.com/NateScarlet/holiday-cn) 项目（数据源通常来自中国政府官方发布）获取指定年份的中国大陆法定节假日和调休安排。
* **智能更新**：自动识别 TinyCal 的日历配置文件路径。
* **选择灵活**：用户可以选择更新当前年份或手动输入特定年份的节假日数据。
* **直接修改**：脚本会直接修改 TinyCal 的本地月份配置文件 (`.0 (zh_CN)` 文件)，将 `worktime` 键值更新 (1 代表补班，2 代表休假)。
* **跨平台兼容**：脚本使用 Python 编写，理论上可以在安装了 Python 环境的 macOS 系统上运行。

## 背景

TinyCal (小历) 是一款简洁美观的 macOS 日历应用，深受用户喜爱。然而，对于依赖准确节假日信息的用户来说，官方数据更新的延迟可能会带来不便。此脚本的初衷就是为了让 TinyCal 用户能够更及时地同步最新的假期安排。

## 使用前提

* **macOS 系统**
* **Python 3 环境**
* **requests 库**: 用于从网络获取节假日数据。如果尚未安装，请通过 pip 安装：
    ```bash
    pip install requests
    # 或者
    pip3 install requests
    ```
* **TinyCal (小历) App 已安装**

## 如何使用

1.  **下载脚本**：
    * 您可以直接从本 GitHub 项目下载 `update_tinycal_holidays.py` (或您为脚本命名的 `.py` 文件)。
    * 或者通过 `git clone` 克隆整个项目。

2.  **备份数据 (强烈建议！)**：
    在运行脚本之前，强烈建议您备份 TinyCal 的日历数据。该数据通常位于：
    `~/Library/Containers/app.cyan.tinycalx/Data/Documents/calendars/`
    您可以将此 `calendars` 文件夹完整复制到其他安全位置。

3.  **运行脚本**：
    打开终端 (Terminal) 应用程序，进入脚本所在的目录，然后执行：
    ```bash
    python update_tinycal_holidays.py
    # 或者，如果您的系统默认 python 指向 python2
    python3 update_tinycal_holidays.py
    ```

4.  **按照提示操作**：
    * 脚本会首先显示将要操作的 TinyCal 日历目录路径。
    * 然后提示您选择是更新今年还是输入特定年份。
        * 输入 `1` 更新当前年份。
        * 输入 `2` 然后按提示输入4位数的年份 (例如 `2025`)。
    * 脚本会自动从网络获取数据并更新相应年份的本地日历文件。

5.  **检查结果**：
    脚本执行完毕后，会显示处理了多少文件，以及有多少文件被实际更新。您可以打开 TinyCal 应用检查对应年份的节假日显示是否已正确更新。

## 工作原理

1.  脚本根据用户选择的年份，从 `https://raw.githubusercontent.com/NateScarlet/holiday-cn/master/{年份}.json` 获取该年度的节假日安排。
2.  解析 JSON 数据，将日期映射为“休假日”或“补班日”。
3.  遍历 TinyCal 的日历数据目录 (`~/Library/Containers/app.cyan.tinycalx/Data/Documents/calendars/`)。
4.  找到与目标年份匹配的月份配置文件 (例如 `2025.5.0 (zh_CN)`）。
5.  读取这些 PList 格式的配置文件，修改其中每一天的 `worktime` 键：
    * `worktime = 2` 表示休假日。
    * `worktime = 1` 表示补班日。
    * 如果日期不是节假日或补班日，则 `worktime` 通常为 `0` (脚本不会修改这些日期的原始值，除非它们在节假日数据中被定义为休假或补班)。
6.  将修改后的配置直接写回原文件。

## 注意事项

* **数据源**：脚本依赖 `NateScarlet/holiday-cn` 项目提供的数据。请确保该数据源的准确性和及时性。
* **应用兼容性**：此脚本是针对特定版本的 TinyCal 文件结构编写的。如果未来 TinyCal 应用的配置文件结构发生重大变化，此脚本可能需要更新。
* **风险提示**：虽然脚本经过测试，但直接修改应用数据总存在一定风险。**请务必在使用前备份您的数据。** 因使用此脚本造成的任何数据丢失或应用问题，作者不承担任何责任。
* **网络连接**：运行脚本时需要有效的互联网连接以下载最新的节假日数据。

## 贡献

欢迎提交 Issue 或 Pull Request 来改进此脚本。

## 致谢

* 感谢 [TinyCal (小历)](https://apps.apple.com/cn/app/%E5%B0%8F%E5%8E%86-%E5%B0%8F%E8%80%8C%E7%BE%8E%E7%9A%84%E6%97%A5%E5%8E%86/id1114272557?mt=12) 应用的开发者。
* 感谢 [NateScarlet/holiday-cn](https://github.com/NateScarlet/holiday-cn) 提供节假日数据。

---

希望这个脚本能帮助您保持 TinyCal 的节假日信息始终最新！
