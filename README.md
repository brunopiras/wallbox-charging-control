# Wallbox Dynamic Charging Controller for Home Assistant

**Author:** bpirasATgmailDOTcom
**Version:** 2025.10.12

## Description

This Python script for Home Assistant provides dynamic control over an EV wallbox, optimizing charging based on real-time data from a photovoltaic (PV) system, a home battery, and overall household consumption. It's designed for users who want to maximize self-consumption of solar energy for EV charging without exporting power to the grid.

The script intelligently adjusts the charging current supplied to the EV, taking into account:
- Total PV power generation.
- Home battery state of charge (SOC) and its charge/discharge rate.
- Total household power consumption.
- Configurable limits to prevent overloading the electrical system.

It is intended to be run via a Home Assistant automation at a frequent interval (e.g., every 45 seconds) to ensure near real-time response to changing conditions.

## Features
- **Dynamic Power Adjustment**: Automatically sets the wallbox charging current based on available surplus solar power.
- **Battery-Aware Charging**: Can prioritize charging the home battery or share power between the battery and the EV based on user-defined SOC thresholds.
- **System Protection**: Monitors total home current and can pause charging to prevent tripping the main breaker.
- **Configurable**: All entity IDs and key operational parameters are centralized in a `CONFIG` dictionary for easy customization.
- **Status Sensor**: Creates and updates a dedicated sensor in Home Assistant (`sensor.wallbox_status`) to provide a real-time overview of the charging status, power flows, and decision logic.
- **Debug Mode**: Includes a debug mode to facilitate troubleshooting.

## Setup

1.  **Copy the Script**: Place the `wallbox_charging_control.py` script into the `/config/python_scripts/` directory of your Home Assistant installation.
2.  **Create Helpers**: In Home Assistant, create all the necessary `input_boolean`, `input_number`, and `input_datetime` helpers defined in the `CONFIG` section of the script. These are used to control and monitor the script's behavior (If you want, use package_wallbox.yaml file to create them automatically).
3.  **Create Template Sensors**: Create any required template sensors that are listed in the `CONFIG` section.
4.  **Automate Execution**: Create a new automation in Home Assistant that calls the `python_script.wallbox_charging_control` service at a regular interval.

    ```yaml
    alias: "Run Wallbox Charging Control"
    trigger:
      - platform: time_pattern
        seconds: "/45"
    action:
      - service: python_script.wallbox_charging_control
    mode: single
    ```
