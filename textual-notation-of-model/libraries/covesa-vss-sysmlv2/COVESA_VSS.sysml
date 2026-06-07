/*
 * SPDX-License-Identifier: MPL-2.0
 * Generated SysML v2 textual library for COVESA Vehicle Signal Specification (VSS).
 * Source: https://github.com/COVESA/vehicle_signal_specification/tree/6fb1dac2630a8910ee996863b2af02b310dcd7ce/spec
 * Scope: leaf VSS attributes, sensors, and actuators reachable from spec/VehicleSignalSpecification.vspec.
 * Unit policy: VSS unit/quantity YAML files are not imported; unit references below point to SysML v2 standard
 * quantity/unit libraries (ISQ/SI/USCustomaryUnits) or derived expressions over those libraries.
 */

package COVESA_VSS {

import ScalarValues::*;
import ISQ::*;
import SI::*;
import USCustomaryUnits::*;

package SignalDefinitions {
  /* VSS path: Vehicle.ADAS.ABS.IsEnabled
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Indicates if ABS is enabled. True = Enabled. False = Disabled.
   */
  attribute def Vehicle_ADAS_ABS_IsEnabled : Boolean;

  /* VSS path: Vehicle.ADAS.ABS.IsEngaged
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if ABS is currently regulating brake pressure. True = Engaged. False = Not Engaged.
   */
  attribute def Vehicle_ADAS_ABS_IsEngaged : Boolean;

  /* VSS path: Vehicle.ADAS.ABS.IsError
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if ABS incurred an error condition. True = Error. False = No Error.
   */
  attribute def Vehicle_ADAS_ABS_IsError : Boolean;

  /* VSS path: Vehicle.ADAS.ActiveAutonomyLevel
   * VSS kind: sensor
   * VSS datatype: string
   * Description: Indicates the currently active level of driving automation according to the SAE J3016 (Taxonomy and Definitions for Terms Related to Driving Automation Systems for On-Road Motor Vehicles).
   * Comment: Complies with https://www.sae.org/standards/content/j3016_202104/ and https://www.sae.org/blog/sae-j3016-update. Level 5 and 4 ADS (Automated driving system) disengage, if appropriate, only after it achieves a minimal risk condition or a driver is performing the DDT. Level 3 ADS disengages either an appropriate time after issuing a request to intervene or immediately upon user request. Level 2 DAS (Driving automation system) disengages immediately upon driver request. However, since many Level 2 DAS, often termed "Level 2.5", warn the driver shortly before reaching their operational limits, the VSS also supports the DISENGAGING state for SAE_2. Nevertheless, it should be noted that the SAE J3016 states that it is incorrect to describe driving automation features using fractional levels.
   * Allowed values: ['SAE_0', 'SAE_1', 'SAE_2_DISENGAGING', 'SAE_2', 'SAE_3_DISENGAGING', 'SAE_3', 'SAE_4_DISENGAGING', 'SAE_4', 'SAE_5_DISENGAGING', 'SAE_5']
   */
  attribute def Vehicle_ADAS_ActiveAutonomyLevel : String;

  /* VSS path: Vehicle.ADAS.CruiseControl.AdaptiveDistanceSet
   * VSS kind: actuator
   * VSS datatype: float
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::metre
   * Description: Distance in meters to keep from lead vehicle
   * Value range: min=0.0, max=
   */
  attribute def Vehicle_ADAS_CruiseControl_AdaptiveDistanceSet : Real;

  /* VSS path: Vehicle.ADAS.CruiseControl.AdaptiveIntervalSet
   * VSS kind: actuator
   * VSS datatype: uint8
   * Description: Follow distance setting, commonly 1-5 with 1 being closest.
   */
  attribute def Vehicle_ADAS_CruiseControl_AdaptiveIntervalSet : Integer;

  /* VSS path: Vehicle.ADAS.CruiseControl.IsActive
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Indicates if cruise control system is active (i.e. actively controls speed). True = Active. False = Inactive.
   */
  attribute def Vehicle_ADAS_CruiseControl_IsActive : Boolean;

  /* VSS path: Vehicle.ADAS.CruiseControl.IsAdaptive
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Indicates if cruise control system is adaptive (i.e. actively controls speed).
   */
  attribute def Vehicle_ADAS_CruiseControl_IsAdaptive : Boolean;

  /* VSS path: Vehicle.ADAS.CruiseControl.IsEnabled
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Indicates if cruise control system is enabled (e.g. ready to receive configurations and settings) True = Enabled. False = Disabled.
   */
  attribute def Vehicle_ADAS_CruiseControl_IsEnabled : Boolean;

  /* VSS path: Vehicle.ADAS.CruiseControl.IsError
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if cruise control system incurred an error condition. True = Error. False = No Error.
   */
  attribute def Vehicle_ADAS_CruiseControl_IsError : Boolean;

  /* VSS path: Vehicle.ADAS.CruiseControl.SpeedSet
   * VSS kind: actuator
   * VSS datatype: float
   * Standard quantity reference: ISQ::speed
   * Standard unit reference: SI::kilometrePerHour
   * Description: Set cruise control speed in kilometers per hour.
   */
  attribute def Vehicle_ADAS_CruiseControl_SpeedSet : Real;

  /* VSS path: Vehicle.ADAS.DMS.IsEnabled
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Indicates if DMS is enabled. True = Enabled. False = Disabled.
   */
  attribute def Vehicle_ADAS_DMS_IsEnabled : Boolean;

  /* VSS path: Vehicle.ADAS.DMS.IsError
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if DMS incurred an error condition. True = Error. False = No Error.
   */
  attribute def Vehicle_ADAS_DMS_IsError : Boolean;

  /* VSS path: Vehicle.ADAS.DMS.IsWarning
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if DMS has registered a driver alert condition.
   */
  attribute def Vehicle_ADAS_DMS_IsWarning : Boolean;

  /* VSS path: Vehicle.ADAS.EBA.IsEnabled
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Indicates if EBA is enabled. True = Enabled. False = Disabled.
   */
  attribute def Vehicle_ADAS_EBA_IsEnabled : Boolean;

  /* VSS path: Vehicle.ADAS.EBA.IsEngaged
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if EBA is currently regulating brake pressure. True = Engaged. False = Not Engaged.
   */
  attribute def Vehicle_ADAS_EBA_IsEngaged : Boolean;

  /* VSS path: Vehicle.ADAS.EBA.IsError
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if EBA incurred an error condition. True = Error. False = No Error.
   */
  attribute def Vehicle_ADAS_EBA_IsError : Boolean;

  /* VSS path: Vehicle.ADAS.EBD.IsEnabled
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Indicates if EBD is enabled. True = Enabled. False = Disabled.
   */
  attribute def Vehicle_ADAS_EBD_IsEnabled : Boolean;

  /* VSS path: Vehicle.ADAS.EBD.IsEngaged
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if EBD is currently regulating vehicle brakeforce distribution. True = Engaged. False = Not Engaged.
   */
  attribute def Vehicle_ADAS_EBD_IsEngaged : Boolean;

  /* VSS path: Vehicle.ADAS.EBD.IsError
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if EBD incurred an error condition. True = Error. False = No Error.
   */
  attribute def Vehicle_ADAS_EBD_IsError : Boolean;

  /* VSS path: Vehicle.ADAS.ESC.IsEnabled
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Indicates if ESC is enabled. True = Enabled. False = Disabled.
   */
  attribute def Vehicle_ADAS_ESC_IsEnabled : Boolean;

  /* VSS path: Vehicle.ADAS.ESC.IsEngaged
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if ESC is currently regulating vehicle stability. True = Engaged. False = Not Engaged.
   */
  attribute def Vehicle_ADAS_ESC_IsEngaged : Boolean;

  /* VSS path: Vehicle.ADAS.ESC.IsError
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if ESC incurred an error condition. True = Error. False = No Error.
   */
  attribute def Vehicle_ADAS_ESC_IsError : Boolean;

  /* VSS path: Vehicle.ADAS.ESC.IsStrongCrossWindDetected
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if the ESC system is detecting strong cross winds. True = Strong cross winds detected. False = No strong cross winds detected.
   */
  attribute def Vehicle_ADAS_ESC_IsStrongCrossWindDetected : Boolean;

  /* VSS path: Vehicle.ADAS.ESC.RoadFriction.LowerBound
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Lower bound road friction, as calculated by the ESC system. 5% possibility that road friction is below this value. 0 = no friction, 100 = maximum friction.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_ADAS_ESC_RoadFriction_LowerBound : Real;

  /* VSS path: Vehicle.ADAS.ESC.RoadFriction.MostProbable
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Most probable road friction, as calculated by the ESC system. Exact meaning of most probable is implementation specific. 0 = no friction, 100 = maximum friction.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_ADAS_ESC_RoadFriction_MostProbable : Real;

  /* VSS path: Vehicle.ADAS.ESC.RoadFriction.UpperBound
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Upper bound road friction, as calculated by the ESC system. 95% possibility that road friction is below this value. 0 = no friction, 100 = maximum friction.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_ADAS_ESC_RoadFriction_UpperBound : Real;

  /* VSS path: Vehicle.ADAS.IsAutoPowerOptimize
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Auto Power Optimization Flag When set to 'true', the system enables automatic power optimization, dynamically adjusting the power optimization level based on runtime conditions or features managed by the OEM. When set to 'false', manual control of the power optimization level is allowed.
   */
  attribute def Vehicle_ADAS_IsAutoPowerOptimize : Boolean;

  /* VSS path: Vehicle.ADAS.LaneDepartureDetection.IsEnabled
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Indicates if lane departure detection system is enabled. True = Enabled. False = Disabled.
   */
  attribute def Vehicle_ADAS_LaneDepartureDetection_IsEnabled : Boolean;

  /* VSS path: Vehicle.ADAS.LaneDepartureDetection.IsError
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if lane departure system incurred an error condition. True = Error. False = No Error.
   */
  attribute def Vehicle_ADAS_LaneDepartureDetection_IsError : Boolean;

  /* VSS path: Vehicle.ADAS.LaneDepartureDetection.IsWarning
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if lane departure detection registered a lane departure.
   */
  attribute def Vehicle_ADAS_LaneDepartureDetection_IsWarning : Boolean;

  /* VSS path: Vehicle.ADAS.ObstacleDetection.Distance
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::metre
   * Description: Distance in meters to detected object
   * Value range: min=0.0, max=
   */
  attribute def Vehicle_ADAS_ObstacleDetection_Distance : Real;

  /* VSS path: Vehicle.ADAS.ObstacleDetection.IsEnabled
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Indicates if obstacle sensor system is enabled (i.e. monitoring for obstacles). True = Enabled. False = Disabled.
   */
  attribute def Vehicle_ADAS_ObstacleDetection_IsEnabled : Boolean;

  /* VSS path: Vehicle.ADAS.ObstacleDetection.IsError
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if obstacle sensor system incurred an error condition. True = Error. False = No Error.
   */
  attribute def Vehicle_ADAS_ObstacleDetection_IsError : Boolean;

  /* VSS path: Vehicle.ADAS.ObstacleDetection.IsWarning
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if obstacle sensor system registered an obstacle.
   */
  attribute def Vehicle_ADAS_ObstacleDetection_IsWarning : Boolean;

  /* VSS path: Vehicle.ADAS.ObstacleDetection.TimeGap
   * VSS kind: sensor
   * VSS datatype: uint32
   * Standard quantity reference: ISQ::time
   * Standard unit reference: SI::millisecond
   * Description: Time in milliseconds before potential impact object
   */
  attribute def Vehicle_ADAS_ObstacleDetection_TimeGap : Integer;

  /* VSS path: Vehicle.ADAS.ObstacleDetection.WarningType
   * VSS kind: sensor
   * VSS datatype: string
   * Description: Indicates the type of obstacle warning detected as some track not only the presence of an obstacle but potential intercepting trajectory or other characteristics.
   * Comment: Undefined obstacle warning type would merely alert of presence of obstacle and may measure distance.
   * Allowed values: ['UNDEFINED', 'CROSS_TRAFFIC', 'BLIND_SPOT']
   */
  attribute def Vehicle_ADAS_ObstacleDetection_WarningType : String;

  /* VSS path: Vehicle.ADAS.PowerOptimizeLevel
   * VSS kind: actuator
   * VSS datatype: uint8
   * Description: Power optimization level for this branch/subsystem. A higher number indicates more aggressive power optimization. Level 0 indicates that all functionality is enabled, no power optimization enabled. Level 10 indicates most aggressive power optimization mode, only essential functionality enabled.
   * Value range: min=0, max=10
   */
  attribute def Vehicle_ADAS_PowerOptimizeLevel : Integer;

  /* VSS path: Vehicle.ADAS.SupportedAutonomyLevel
   * VSS kind: attribute
   * VSS datatype: string
   * Description: Indicates the highest level of driving automation according to the SAE J3016 taxonomy the vehicle is capable of.
   * Allowed values: ['SAE_0', 'SAE_1', 'SAE_2', 'SAE_3', 'SAE_4', 'SAE_5']
   */
  attribute def Vehicle_ADAS_SupportedAutonomyLevel : String;

  /* VSS path: Vehicle.ADAS.TCS.IsEnabled
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Indicates if TCS is enabled. True = Enabled. False = Disabled.
   */
  attribute def Vehicle_ADAS_TCS_IsEnabled : Boolean;

  /* VSS path: Vehicle.ADAS.TCS.IsEngaged
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if TCS is currently regulating traction. True = Engaged. False = Not Engaged.
   */
  attribute def Vehicle_ADAS_TCS_IsEngaged : Boolean;

  /* VSS path: Vehicle.ADAS.TCS.IsError
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if TCS incurred an error condition. True = Error. False = No Error.
   */
  attribute def Vehicle_ADAS_TCS_IsError : Boolean;

  /* VSS path: Vehicle.Acceleration.Lateral
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::acceleration
   * Standard unit reference: SI::metrePerSecondSquared
   * Description: Vehicle acceleration in Y (lateral acceleration).
   */
  attribute def Vehicle_Acceleration_Lateral : Real;

  /* VSS path: Vehicle.Acceleration.Longitudinal
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::acceleration
   * Standard unit reference: SI::metrePerSecondSquared
   * Description: Vehicle acceleration in X (longitudinal acceleration).
   */
  attribute def Vehicle_Acceleration_Longitudinal : Real;

  /* VSS path: Vehicle.Acceleration.Vertical
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::acceleration
   * Standard unit reference: SI::metrePerSecondSquared
   * Description: Vehicle acceleration in Z (vertical acceleration).
   */
  attribute def Vehicle_Acceleration_Vertical : Real;

  /* VSS path: Vehicle.AngularVelocity.Pitch
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::angularVelocity
   * Standard unit reference: SI::degreePerSecond
   * Description: Vehicle rotation rate along Y (lateral).
   */
  attribute def Vehicle_AngularVelocity_Pitch : Real;

  /* VSS path: Vehicle.AngularVelocity.Roll
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::angularVelocity
   * Standard unit reference: SI::degreePerSecond
   * Description: Vehicle rotation rate along X (longitudinal).
   */
  attribute def Vehicle_AngularVelocity_Roll : Real;

  /* VSS path: Vehicle.AngularVelocity.Yaw
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::angularVelocity
   * Standard unit reference: SI::degreePerSecond
   * Description: Vehicle rotation rate along Z (vertical).
   */
  attribute def Vehicle_AngularVelocity_Yaw : Real;

  /* VSS path: Vehicle.AverageSpeed
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::speed
   * Standard unit reference: SI::kilometrePerHour
   * Description: Average speed for the current trip.
   * Comment: A new trip is considered to start when engine gets enabled (e.g. LowVoltageSystemState in ON or START mode). A trip is considered to end when engine is no longer enabled. The signal may however keep the value of the last trip until a new trip is started. Calculation of average speed may exclude periods when the vehicle for example is not moving or transmission is in neutral.
   */
  attribute def Vehicle_AverageSpeed : Real;

  /* VSS path: Vehicle.Body.BodyType
   * VSS kind: attribute
   * VSS datatype: string
   * Description: Body type code as defined by ISO 3779.
   */
  attribute def Vehicle_Body_BodyType : String;

  /* VSS path: Vehicle.Body.Hood.IsOpen
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is item open or closed? True = Fully or partially open. False = Fully closed.
   */
  attribute def Vehicle_Body_Hood_IsOpen : Boolean;

  /* VSS path: Vehicle.Body.Hood.Position
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Item position. 0 = Start position 100 = End position.
   * Comment: Relationship between Open/Close and Start/End position is item dependent.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Body_Hood_Position : Integer;

  /* VSS path: Vehicle.Body.Hood.Switch
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Switch controlling sliding action such as window, sunroof, or blind.
   * Allowed values: ['INACTIVE', 'CLOSE', 'OPEN', 'ONE_SHOT_CLOSE', 'ONE_SHOT_OPEN']
   */
  attribute def Vehicle_Body_Hood_Switch : String;

  /* VSS path: Vehicle.Body.Horn.IsActive
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Horn active or inactive. True = Active. False = Inactive.
   */
  attribute def Vehicle_Body_Horn_IsActive : Boolean;

  /* VSS path: Vehicle.Body.IsAutoPowerOptimize
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Auto Power Optimization Flag When set to 'true', the system enables automatic power optimization, dynamically adjusting the power optimization level based on runtime conditions or features managed by the OEM. When set to 'false', manual control of the power optimization level is allowed.
   */
  attribute def Vehicle_Body_IsAutoPowerOptimize : Boolean;

  /* VSS path: Vehicle.Body.Lights.Backup.IsDefect
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if light is defect. True = Light is defect. False = Light has no defect.
   */
  attribute def Vehicle_Body_Lights_Backup_IsDefect : Boolean;

  /* VSS path: Vehicle.Body.Lights.Backup.IsOn
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Indicates if light is on or off. True = On. False = Off.
   */
  attribute def Vehicle_Body_Lights_Backup_IsOn : Boolean;

  /* VSS path: Vehicle.Body.Lights.Beam.IsDefect
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if light is defect. True = Light is defect. False = Light has no defect.
   */
  attribute def Vehicle_Body_Lights_Beam_IsDefect : Boolean;

  /* VSS path: Vehicle.Body.Lights.Beam.IsOn
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Indicates if light is on or off. True = On. False = Off.
   */
  attribute def Vehicle_Body_Lights_Beam_IsOn : Boolean;

  /* VSS path: Vehicle.Body.Lights.Brake.IsActive
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Indicates if break-light is active. INACTIVE means lights are off. ACTIVE means lights are on. ADAPTIVE means that break-light is indicating emergency-breaking.
   * Allowed values: ['INACTIVE', 'ACTIVE', 'ADAPTIVE']
   */
  attribute def Vehicle_Body_Lights_Brake_IsActive : String;

  /* VSS path: Vehicle.Body.Lights.Brake.IsDefect
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if light is defect. True = Light is defect. False = Light has no defect.
   */
  attribute def Vehicle_Body_Lights_Brake_IsDefect : Boolean;

  /* VSS path: Vehicle.Body.Lights.DirectionIndicator.IsDefect
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if light is defect. True = Light is defect. False = Light has no defect.
   */
  attribute def Vehicle_Body_Lights_DirectionIndicator_IsDefect : Boolean;

  /* VSS path: Vehicle.Body.Lights.DirectionIndicator.IsSignaling
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Indicates if light is signaling or off. True = signaling. False = Off.
   */
  attribute def Vehicle_Body_Lights_DirectionIndicator_IsSignaling : Boolean;

  /* VSS path: Vehicle.Body.Lights.Fog.IsDefect
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if light is defect. True = Light is defect. False = Light has no defect.
   */
  attribute def Vehicle_Body_Lights_Fog_IsDefect : Boolean;

  /* VSS path: Vehicle.Body.Lights.Fog.IsOn
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Indicates if light is on or off. True = On. False = Off.
   */
  attribute def Vehicle_Body_Lights_Fog_IsOn : Boolean;

  /* VSS path: Vehicle.Body.Lights.Hazard.IsDefect
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if light is defect. True = Light is defect. False = Light has no defect.
   */
  attribute def Vehicle_Body_Lights_Hazard_IsDefect : Boolean;

  /* VSS path: Vehicle.Body.Lights.Hazard.IsSignaling
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Indicates if light is signaling or off. True = signaling. False = Off.
   */
  attribute def Vehicle_Body_Lights_Hazard_IsSignaling : Boolean;

  /* VSS path: Vehicle.Body.Lights.IsHighBeamSwitchOn
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Status of the high beam switch. True = high beam enabled. False = high beam not enabled.
   * Comment: This signal indicates the status of the switch and does not indicate if low or high beam actually are on. That typically depends on vehicle logic and other signals like Lights.LightSwitch and Vehicle.LowVoltageSystemState.
   */
  attribute def Vehicle_Body_Lights_IsHighBeamSwitchOn : Boolean;

  /* VSS path: Vehicle.Body.Lights.LicensePlate.IsDefect
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if light is defect. True = Light is defect. False = Light has no defect.
   */
  attribute def Vehicle_Body_Lights_LicensePlate_IsDefect : Boolean;

  /* VSS path: Vehicle.Body.Lights.LicensePlate.IsOn
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Indicates if light is on or off. True = On. False = Off.
   */
  attribute def Vehicle_Body_Lights_LicensePlate_IsOn : Boolean;

  /* VSS path: Vehicle.Body.Lights.LightSwitch
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Status of the vehicle main light switch.
   * Comment: A vehicle typically does not support all alternatives. Which lights that actually are lit may vary according to vehicle configuration and local legislation. OFF is typically indicated by 0. POSITION is typically indicated by ISO 7000 symbol 0456. DAYTIME_RUNNING_LIGHTS (DRL) can be indicated by ISO 7000 symbol 2611. AUTO indicates that vehicle automatically selects suitable lights. BEAM is typically indicated by ISO 7000 symbol 0083.
   * Allowed values: ['OFF', 'POSITION', 'DAYTIME_RUNNING_LIGHTS', 'AUTO', 'BEAM']
   */
  attribute def Vehicle_Body_Lights_LightSwitch : String;

  /* VSS path: Vehicle.Body.Lights.Parking.IsDefect
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if light is defect. True = Light is defect. False = Light has no defect.
   */
  attribute def Vehicle_Body_Lights_Parking_IsDefect : Boolean;

  /* VSS path: Vehicle.Body.Lights.Parking.IsOn
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Indicates if light is on or off. True = On. False = Off.
   */
  attribute def Vehicle_Body_Lights_Parking_IsOn : Boolean;

  /* VSS path: Vehicle.Body.Lights.Running.IsDefect
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if light is defect. True = Light is defect. False = Light has no defect.
   */
  attribute def Vehicle_Body_Lights_Running_IsDefect : Boolean;

  /* VSS path: Vehicle.Body.Lights.Running.IsOn
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Indicates if light is on or off. True = On. False = Off.
   */
  attribute def Vehicle_Body_Lights_Running_IsOn : Boolean;

  /* VSS path: Vehicle.Body.Mirrors.IsFolded
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is mirror folded? True = Fully or partially folded. False = Fully unfolded.
   */
  attribute def Vehicle_Body_Mirrors_IsFolded : Boolean;

  /* VSS path: Vehicle.Body.Mirrors.IsHeatingOn
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Mirror Heater on or off. True = Heater On. False = Heater Off.
   */
  attribute def Vehicle_Body_Mirrors_IsHeatingOn : Boolean;

  /* VSS path: Vehicle.Body.Mirrors.IsLocked
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is mirror movement locked? True = Locked, mirror will not react to Tilt/Pan change. False = Unlocked.
   */
  attribute def Vehicle_Body_Mirrors_IsLocked : Boolean;

  /* VSS path: Vehicle.Body.Mirrors.Pan
   * VSS kind: actuator
   * VSS datatype: int8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Mirror pan as a percent. 0 = Center Position. 100 = Fully Left Position. -100 = Fully Right Position.
   * Value range: min=-100, max=100
   */
  attribute def Vehicle_Body_Mirrors_Pan : Integer;

  /* VSS path: Vehicle.Body.Mirrors.Tilt
   * VSS kind: actuator
   * VSS datatype: int8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Mirror tilt as a percent. 0 = Center Position. 100 = Fully Upward Position. -100 = Fully Downward Position.
   * Value range: min=-100, max=100
   */
  attribute def Vehicle_Body_Mirrors_Tilt : Integer;

  /* VSS path: Vehicle.Body.Mirrors.Yaw
   * VSS kind: actuator
   * VSS datatype: int8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Relative mirror yaw angle, measured from the vehicle sprung mass X-axis as defined by ISO 23150:2023 to the mirror X-axis, around the vehicle Z-axis (right-hand rule). 0 = Mirror in default position. Exact position (yaw relative to vehicle X-axis) is vehicle dependent. 100 = Maximum yaw. Mirror rotated clockwise as much as possible around Z-axis. -100 = Minimum yaw. Mirror rotated counter-clockwise as much as possible around Z-axis.
   * Comment: A positive yaw indicates that the mirror has been adjusted to get a better view on objects on the right side of the vehicle.
   * Value range: min=-100, max=100
   */
  attribute def Vehicle_Body_Mirrors_Yaw : Integer;

  /* VSS path: Vehicle.Body.PowerOptimizeLevel
   * VSS kind: actuator
   * VSS datatype: uint8
   * Description: Power optimization level for this branch/subsystem. A higher number indicates more aggressive power optimization. Level 0 indicates that all functionality is enabled, no power optimization enabled. Level 10 indicates most aggressive power optimization mode, only essential functionality enabled.
   * Value range: min=0, max=10
   */
  attribute def Vehicle_Body_PowerOptimizeLevel : Integer;

  /* VSS path: Vehicle.Body.Raindetection.Intensity
   * VSS kind: sensor
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Rain intensity. 0 = Dry, No Rain. 100 = Covered.
   * Value range: min=, max=100
   */
  attribute def Vehicle_Body_Raindetection_Intensity : Integer;

  /* VSS path: Vehicle.Body.RearMainSpoilerPosition
   * VSS kind: actuator
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Rear spoiler position, 0% = Spoiler fully stowed. 100% = Spoiler fully exposed.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Body_RearMainSpoilerPosition : Real;

  /* VSS path: Vehicle.Body.Trunk.IsLightOn
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is trunk light on
   * Comment: V4.0 Moved from Vehicle.Cabin.Lights.IsTrunkOn because Trunk is not defined as part of the Cabin.
   */
  attribute def Vehicle_Body_Trunk_IsLightOn : Boolean;

  /* VSS path: Vehicle.Body.Trunk.IsLocked
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is item locked or unlocked. True = Locked. False = Unlocked.
   */
  attribute def Vehicle_Body_Trunk_IsLocked : Boolean;

  /* VSS path: Vehicle.Body.Trunk.IsOpen
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is item open or closed? True = Fully or partially open. False = Fully closed.
   */
  attribute def Vehicle_Body_Trunk_IsOpen : Boolean;

  /* VSS path: Vehicle.Body.Trunk.Position
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Item position. 0 = Start position 100 = End position.
   * Comment: Relationship between Open/Close and Start/End position is item dependent.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Body_Trunk_Position : Integer;

  /* VSS path: Vehicle.Body.Trunk.Switch
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Switch controlling sliding action such as window, sunroof, or blind.
   * Allowed values: ['INACTIVE', 'CLOSE', 'OPEN', 'ONE_SHOT_CLOSE', 'ONE_SHOT_OPEN']
   */
  attribute def Vehicle_Body_Trunk_Switch : String;

  /* VSS path: Vehicle.Body.Windshield.IsHeatingOn
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Windshield heater status. False - off, True - on.
   */
  attribute def Vehicle_Body_Windshield_IsHeatingOn : Boolean;

  /* VSS path: Vehicle.Body.Windshield.WasherFluid.IsLevelLow
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Low level indication for washer fluid. True = Level Low. False = Level OK.
   */
  attribute def Vehicle_Body_Windshield_WasherFluid_IsLevelLow : Boolean;

  /* VSS path: Vehicle.Body.Windshield.WasherFluid.Level
   * VSS kind: sensor
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Washer fluid level as a percent. 0 = Empty. 100 = Full.
   * Value range: min=, max=100
   */
  attribute def Vehicle_Body_Windshield_WasherFluid_Level : Integer;

  /* VSS path: Vehicle.Body.Windshield.Wiping.Intensity
   * VSS kind: actuator
   * VSS datatype: uint8
   * Description: Relative intensity/sensitivity for interval and rain sensor mode as requested by user/driver. Has no significance if Windshield.Wiping.Mode is OFF/SLOW/MEDIUM/FAST 0 - wipers inactive. 1 - minimum intensity (lowest frequency/sensitivity, longest interval). 2/3/4/... - higher intensity (higher frequency/sensitivity, shorter interval). Maximum value supported is vehicle specific.
   */
  attribute def Vehicle_Body_Windshield_Wiping_Intensity : Integer;

  /* VSS path: Vehicle.Body.Windshield.Wiping.IsWipersWorn
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Wiper wear status. True = Worn, Replacement recommended or required. False = Not Worn.
   */
  attribute def Vehicle_Body_Windshield_Wiping_IsWipersWorn : Boolean;

  /* VSS path: Vehicle.Body.Windshield.Wiping.Mode
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Wiper mode requested by user/driver. INTERVAL indicates intermittent wiping, with fixed time interval between each wipe. RAIN_SENSOR indicates intermittent wiping based on rain intensity.
   * Allowed values: ['OFF', 'SLOW', 'MEDIUM', 'FAST', 'INTERVAL', 'RAIN_SENSOR']
   */
  attribute def Vehicle_Body_Windshield_Wiping_Mode : String;

  /* VSS path: Vehicle.Body.Windshield.Wiping.System.ActualPosition
   * VSS kind: actuator
   * VSS datatype: float
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Actual position of main wiper blade for the wiper system relative to reference position. Location of reference position (0 degrees) and direction of positive/negative degrees is vehicle specific.
   * Comment: Default parking position might be used as reference position.
   */
  attribute def Vehicle_Body_Windshield_Wiping_System_ActualPosition : Real;

  /* VSS path: Vehicle.Body.Windshield.Wiping.System.DriveCurrent
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::electricCurrent
   * Standard unit reference: SI::ampere
   * Description: Actual current used by wiper drive.
   * Comment: May be negative in special situations.
   */
  attribute def Vehicle_Body_Windshield_Wiping_System_DriveCurrent : Real;

  /* VSS path: Vehicle.Body.Windshield.Wiping.System.Frequency
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::frequency
   * Standard unit reference: SI-derived cycles/minute
   * Description: Wiping frequency/speed, measured in cycles per minute. The signal concerns the actual speed of the wiper blades when moving. Intervals/pauses are excluded, i.e. the value corresponds to the number of cycles that would be completed in 1 minute if wiping permanently over default range.
   * Comment: Examples - 0 = Wipers stopped, 80 = Wipers doing 80 cycles per minute (in WIPE mode).
   */
  attribute def Vehicle_Body_Windshield_Wiping_System_Frequency : Integer;

  /* VSS path: Vehicle.Body.Windshield.Wiping.System.IsBlocked
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if wiper movement is blocked. True = Movement blocked. False = Movement not blocked.
   */
  attribute def Vehicle_Body_Windshield_Wiping_System_IsBlocked : Boolean;

  /* VSS path: Vehicle.Body.Windshield.Wiping.System.IsEndingWipeCycle
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if current wipe movement is completed or near completion. True = Movement is completed or near completion. Changes to RequestedPosition will be executed first after reaching previous RequestedPosition, if it has not already been reached. False = Movement is not near completion. Any change to RequestedPosition will be executed immediately. Change of direction may not be allowed.
   * Comment: In continuous wiping between A and B this sensor can be used a trigger to update TargetPosition.
   */
  attribute def Vehicle_Body_Windshield_Wiping_System_IsEndingWipeCycle : Boolean;

  /* VSS path: Vehicle.Body.Windshield.Wiping.System.IsOverheated
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if wiper system is overheated. True = Wiper system overheated. False = Wiper system not overheated.
   */
  attribute def Vehicle_Body_Windshield_Wiping_System_IsOverheated : Boolean;

  /* VSS path: Vehicle.Body.Windshield.Wiping.System.IsPositionReached
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if a requested position has been reached. IsPositionReached refers to the previous position in case the TargetPosition is updated while IsEndingWipeCycle=True. True = Current or Previous TargetPosition reached. False = Position not (yet) reached, or wipers have moved away from the reached position.
   */
  attribute def Vehicle_Body_Windshield_Wiping_System_IsPositionReached : Boolean;

  /* VSS path: Vehicle.Body.Windshield.Wiping.System.IsWiperError
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates system failure. True if wiping is disabled due to system failure.
   */
  attribute def Vehicle_Body_Windshield_Wiping_System_IsWiperError : Boolean;

  /* VSS path: Vehicle.Body.Windshield.Wiping.System.IsWiping
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates wiper movement. True if wiper blades are moving. Change of direction shall be considered as IsWiping if wipers will continue to move directly after the change of direction.
   */
  attribute def Vehicle_Body_Windshield_Wiping_System_IsWiping : Boolean;

  /* VSS path: Vehicle.Body.Windshield.Wiping.System.Mode
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Requested mode of wiper system. STOP_HOLD means that the wipers shall move to position given by TargetPosition and then hold the position. WIPE means that wipers shall move to the position given by TargetPosition and then hold the position if no new TargetPosition is requested. PLANT_MODE means that wiping is disabled. Exact behavior is vehicle specific. EMERGENCY_STOP means that wiping shall be immediately stopped without holding the position.
   * Allowed values: ['STOP_HOLD', 'WIPE', 'PLANT_MODE', 'EMERGENCY_STOP']
   */
  attribute def Vehicle_Body_Windshield_Wiping_System_Mode : String;

  /* VSS path: Vehicle.Body.Windshield.Wiping.System.TargetPosition
   * VSS kind: actuator
   * VSS datatype: float
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Requested position of main wiper blade for the wiper system relative to reference position. Location of reference position (0 degrees) and direction of positive/negative degrees is vehicle specific. System behavior when receiving TargetPosition depends on Mode and IsEndingWipeCycle. Supported values are vehicle specific and might be dynamically corrected. If IsEndingWipeCycle=True then wipers will complete current movement before actuating new TargetPosition. If IsEndingWipeCycle=False then wipers will directly change destination if the TargetPosition is changed.
   * Comment: Default parking position might be used as reference position.
   */
  attribute def Vehicle_Body_Windshield_Wiping_System_TargetPosition : Real;

  /* VSS path: Vehicle.Body.Windshield.Wiping.WiperWear
   * VSS kind: sensor
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Wiper wear as percent. 0 = No Wear. 100 = Worn. Replacement required. Method for calculating or estimating wiper wear is vehicle specific. For windshields with multiple wipers the wear reported shall correspond to the most worn wiper.
   * Value range: min=, max=100
   */
  attribute def Vehicle_Body_Windshield_Wiping_WiperWear : Integer;

  /* VSS path: Vehicle.Cabin.Convertible.Status
   * VSS kind: sensor
   * VSS datatype: string
   * Description: Roof status on convertible vehicles.
   * Allowed values: ['UNDEFINED', 'CLOSED', 'OPEN', 'CLOSING', 'OPENING', 'STALLED']
   */
  attribute def Vehicle_Cabin_Convertible_Status : String;

  /* VSS path: Vehicle.Cabin.Door.IsChildLockActive
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Is door child lock active. True = Door cannot be opened from inside. False = Door can be opened from inside.
   */
  attribute def Vehicle_Cabin_Door_IsChildLockActive : Boolean;

  /* VSS path: Vehicle.Cabin.Door.IsLocked
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is item locked or unlocked. True = Locked. False = Unlocked.
   */
  attribute def Vehicle_Cabin_Door_IsLocked : Boolean;

  /* VSS path: Vehicle.Cabin.Door.IsOpen
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is item open or closed? True = Fully or partially open. False = Fully closed.
   */
  attribute def Vehicle_Cabin_Door_IsOpen : Boolean;

  /* VSS path: Vehicle.Cabin.Door.Position
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Item position. 0 = Start position 100 = End position.
   * Comment: Relationship between Open/Close and Start/End position is item dependent.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Cabin_Door_Position : Integer;

  /* VSS path: Vehicle.Cabin.Door.Shade.IsOpen
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is item open or closed? True = Fully or partially open. False = Fully closed.
   */
  attribute def Vehicle_Cabin_Door_Shade_IsOpen : Boolean;

  /* VSS path: Vehicle.Cabin.Door.Shade.Position
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Item position. 0 = Start position 100 = End position.
   * Comment: Relationship between Open/Close and Start/End position is item dependent.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Cabin_Door_Shade_Position : Integer;

  /* VSS path: Vehicle.Cabin.Door.Shade.Switch
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Switch controlling sliding action such as window, sunroof, or blind.
   * Allowed values: ['INACTIVE', 'CLOSE', 'OPEN', 'ONE_SHOT_CLOSE', 'ONE_SHOT_OPEN']
   */
  attribute def Vehicle_Cabin_Door_Shade_Switch : String;

  /* VSS path: Vehicle.Cabin.Door.Switch
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Switch controlling sliding action such as window, sunroof, or blind.
   * Allowed values: ['INACTIVE', 'CLOSE', 'OPEN', 'ONE_SHOT_CLOSE', 'ONE_SHOT_OPEN']
   */
  attribute def Vehicle_Cabin_Door_Switch : String;

  /* VSS path: Vehicle.Cabin.Door.Window.IsOpen
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is item open or closed? True = Fully or partially open. False = Fully closed.
   */
  attribute def Vehicle_Cabin_Door_Window_IsOpen : Boolean;

  /* VSS path: Vehicle.Cabin.Door.Window.Position
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Item position. 0 = Start position 100 = End position.
   * Comment: Relationship between Open/Close and Start/End position is item dependent.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Cabin_Door_Window_Position : Integer;

  /* VSS path: Vehicle.Cabin.Door.Window.Switch
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Switch controlling sliding action such as window, sunroof, or blind.
   * Allowed values: ['INACTIVE', 'CLOSE', 'OPEN', 'ONE_SHOT_CLOSE', 'ONE_SHOT_OPEN']
   */
  attribute def Vehicle_Cabin_Door_Window_Switch : String;

  /* VSS path: Vehicle.Cabin.DoorCount
   * VSS kind: attribute
   * VSS datatype: uint8
   * Description: Number of doors in vehicle.
   */
  attribute def Vehicle_Cabin_DoorCount : Integer;

  /* VSS path: Vehicle.Cabin.DriverPosition
   * VSS kind: attribute
   * VSS datatype: string
   * Description: The position of the driver seat in row 1.
   * Comment: Some signals use DriverSide and PassengerSide as instances. If this signal specifies that DriverPosition is LEFT or MIDDLE, then DriverSide refers to left side and PassengerSide to right side. If this signal specifies that DriverPosition is RIGHT, then DriverSide refers to right side and PassengerSide to left side.
   * Allowed values: ['LEFT', 'MIDDLE', 'RIGHT']
   */
  attribute def Vehicle_Cabin_DriverPosition : String;

  /* VSS path: Vehicle.Cabin.HVAC.AmbientAirTemperature
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::thermodynamicTemperature
   * Standard unit reference: SI::degreeCelsius
   * Description: Ambient air temperature inside the vehicle.
   */
  attribute def Vehicle_Cabin_HVAC_AmbientAirTemperature : Real;

  /* VSS path: Vehicle.Cabin.HVAC.IsAirConditioningActive
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is Air conditioning active.
   */
  attribute def Vehicle_Cabin_HVAC_IsAirConditioningActive : Boolean;

  /* VSS path: Vehicle.Cabin.HVAC.IsAutoPowerOptimize
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Auto Power Optimization Flag When set to 'true', the system enables automatic power optimization, dynamically adjusting the power optimization level based on runtime conditions or features managed by the OEM. When set to 'false', manual control of the power optimization level is allowed.
   */
  attribute def Vehicle_Cabin_HVAC_IsAutoPowerOptimize : Boolean;

  /* VSS path: Vehicle.Cabin.HVAC.IsFrontDefrosterActive
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is front defroster active.
   */
  attribute def Vehicle_Cabin_HVAC_IsFrontDefrosterActive : Boolean;

  /* VSS path: Vehicle.Cabin.HVAC.IsRearDefrosterActive
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is rear defroster active.
   */
  attribute def Vehicle_Cabin_HVAC_IsRearDefrosterActive : Boolean;

  /* VSS path: Vehicle.Cabin.HVAC.IsRecirculationActive
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is recirculation active.
   */
  attribute def Vehicle_Cabin_HVAC_IsRecirculationActive : Boolean;

  /* VSS path: Vehicle.Cabin.HVAC.PowerOptimizeLevel
   * VSS kind: actuator
   * VSS datatype: uint8
   * Description: Power optimization level for this branch/subsystem. A higher number indicates more aggressive power optimization. Level 0 indicates that all functionality is enabled, no power optimization enabled. Level 10 indicates most aggressive power optimization mode, only essential functionality enabled.
   * Value range: min=0, max=10
   */
  attribute def Vehicle_Cabin_HVAC_PowerOptimizeLevel : Integer;

  /* VSS path: Vehicle.Cabin.HVAC.Station.AirDistribution
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Direction of airstream
   * Allowed values: ['UP', 'MIDDLE', 'DOWN']
   */
  attribute def Vehicle_Cabin_HVAC_Station_AirDistribution : String;

  /* VSS path: Vehicle.Cabin.HVAC.Station.FanSpeed
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Fan Speed, 0 = off. 100 = max
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Cabin_HVAC_Station_FanSpeed : Integer;

  /* VSS path: Vehicle.Cabin.HVAC.Station.Temperature
   * VSS kind: actuator
   * VSS datatype: float
   * Standard quantity reference: ISQ::thermodynamicTemperature
   * Standard unit reference: SI::degreeCelsius
   * Description: Temperature
   */
  attribute def Vehicle_Cabin_HVAC_Station_Temperature : Real;

  /* VSS path: Vehicle.Cabin.Infotainment.HMI.Brightness
   * VSS kind: actuator
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Brightness of the HMI, relative to supported range. 0 = Lowest brightness possible. 100 = Maximum Brightness possible.
   * Comment: The value 0 does not necessarily correspond to a turned off HMI, as it may not be allowed/supported to turn off the HMI completely.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Cabin_Infotainment_HMI_Brightness : Real;

  /* VSS path: Vehicle.Cabin.Infotainment.HMI.CurrentLanguage
   * VSS kind: sensor
   * VSS datatype: string
   * Description: ISO 639-1 standard language code for the current HMI
   */
  attribute def Vehicle_Cabin_Infotainment_HMI_CurrentLanguage : String;

  /* VSS path: Vehicle.Cabin.Infotainment.HMI.DateFormat
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Date format used in the current HMI
   * Allowed values: ['YYYY_MM_DD', 'DD_MM_YYYY', 'MM_DD_YYYY', 'YY_MM_DD', 'DD_MM_YY', 'MM_DD_YY']
   */
  attribute def Vehicle_Cabin_Infotainment_HMI_DateFormat : String;

  /* VSS path: Vehicle.Cabin.Infotainment.HMI.DayNightMode
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Current display theme
   * Allowed values: ['DAY', 'NIGHT']
   */
  attribute def Vehicle_Cabin_Infotainment_HMI_DayNightMode : String;

  /* VSS path: Vehicle.Cabin.Infotainment.HMI.DisplayOffDuration
   * VSS kind: actuator
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::time
   * Standard unit reference: SI::second
   * Description: Duration in seconds before the display is turned off. Value shall be 0 if screen never shall turn off.
   * Comment: Display shall be turned off at HMI.LastActionTime + HMI.DisplayOffDuration, unless HMI.IsScreenAlwaysOn==True.
   */
  attribute def Vehicle_Cabin_Infotainment_HMI_DisplayOffDuration : Integer;

  /* VSS path: Vehicle.Cabin.Infotainment.HMI.DistanceUnit
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Distance unit used in the current HMI
   * Allowed values: ['MILES', 'KILOMETERS']
   */
  attribute def Vehicle_Cabin_Infotainment_HMI_DistanceUnit : String;

  /* VSS path: Vehicle.Cabin.Infotainment.HMI.EVEconomyUnits
   * VSS kind: actuator
   * VSS datatype: string
   * Description: EV fuel economy unit used in the current HMI
   * Allowed values: ['MILES_PER_KILOWATT_HOUR', 'KILOMETERS_PER_KILOWATT_HOUR', 'KILOWATT_HOURS_PER_100_MILES', 'KILOWATT_HOURS_PER_100_KILOMETERS', 'WATT_HOURS_PER_MILE', 'WATT_HOURS_PER_KILOMETER']
   */
  attribute def Vehicle_Cabin_Infotainment_HMI_EVEconomyUnits : String;

  /* VSS path: Vehicle.Cabin.Infotainment.HMI.EVEnergyUnits
   * VSS kind: actuator
   * VSS datatype: string
   * Description: EV energy unit used in the current HMI
   * Comment: Ampere hours is by definition not an energy unit, but can be used as a measurement of energy if the voltage, like nominal voltage of the battery, is known.
   * Allowed values: ['WATT_HOURS', 'AMPERE_HOURS', 'KILOWATT_HOURS']
   */
  attribute def Vehicle_Cabin_Infotainment_HMI_EVEnergyUnits : String;

  /* VSS path: Vehicle.Cabin.Infotainment.HMI.FontSize
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Font size used in the current HMI
   * Allowed values: ['STANDARD', 'LARGE', 'EXTRA_LARGE']
   */
  attribute def Vehicle_Cabin_Infotainment_HMI_FontSize : String;

  /* VSS path: Vehicle.Cabin.Infotainment.HMI.FuelEconomyUnits
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Fuel economy unit used in the current HMI
   * Allowed values: ['MPG_UK', 'MPG_US', 'MILES_PER_LITER', 'KILOMETERS_PER_LITER', 'LITERS_PER_100_KILOMETERS']
   */
  attribute def Vehicle_Cabin_Infotainment_HMI_FuelEconomyUnits : String;

  /* VSS path: Vehicle.Cabin.Infotainment.HMI.FuelVolumeUnit
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Fuel volume unit used in the current HMI
   * Allowed values: ['LITER', 'GALLON_US', 'GALLON_UK']
   */
  attribute def Vehicle_Cabin_Infotainment_HMI_FuelVolumeUnit : String;

  /* VSS path: Vehicle.Cabin.Infotainment.HMI.IsScreenAlwaysOn
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Used to prevent the screen going black if no action placed.
   */
  attribute def Vehicle_Cabin_Infotainment_HMI_IsScreenAlwaysOn : Boolean;

  /* VSS path: Vehicle.Cabin.Infotainment.HMI.LastActionTime
   * VSS kind: sensor
   * VSS datatype: string
   * Standard quantity reference: n/a
   * Standard unit reference: ISO 8601 lexical date/time string
   * Description: Time for last hmi action, formatted according to ISO 8601 with UTC time zone.
   */
  attribute def Vehicle_Cabin_Infotainment_HMI_LastActionTime : String;

  /* VSS path: Vehicle.Cabin.Infotainment.HMI.SpeedUnit
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Speed unit used in the current HMI
   * Allowed values: ['METERS_PER_SECOND', 'MILES_PER_HOUR', 'KILOMETERS_PER_HOUR']
   */
  attribute def Vehicle_Cabin_Infotainment_HMI_SpeedUnit : String;

  /* VSS path: Vehicle.Cabin.Infotainment.HMI.TemperatureUnit
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Temperature unit used in the current HMI
   * Allowed values: ['C', 'F']
   */
  attribute def Vehicle_Cabin_Infotainment_HMI_TemperatureUnit : String;

  /* VSS path: Vehicle.Cabin.Infotainment.HMI.TimeFormat
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Time format used in the current HMI
   * Allowed values: ['HR_12', 'HR_24']
   */
  attribute def Vehicle_Cabin_Infotainment_HMI_TimeFormat : String;

  /* VSS path: Vehicle.Cabin.Infotainment.HMI.TirePressureUnit
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Tire pressure unit used in the current HMI
   * Allowed values: ['PSI', 'KPA', 'BAR']
   */
  attribute def Vehicle_Cabin_Infotainment_HMI_TirePressureUnit : String;

  /* VSS path: Vehicle.Cabin.Infotainment.IsAutoPowerOptimize
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Auto Power Optimization Flag When set to 'true', the system enables automatic power optimization, dynamically adjusting the power optimization level based on runtime conditions or features managed by the OEM. When set to 'false', manual control of the power optimization level is allowed.
   */
  attribute def Vehicle_Cabin_Infotainment_IsAutoPowerOptimize : Boolean;

  /* VSS path: Vehicle.Cabin.Infotainment.Media.Action
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Tells if the media was
   * Allowed values: ['UNKNOWN', 'STOP', 'PLAY', 'FAST_FORWARD', 'FAST_BACKWARD', 'SKIP_FORWARD', 'SKIP_BACKWARD']
   */
  attribute def Vehicle_Cabin_Infotainment_Media_Action : String;

  /* VSS path: Vehicle.Cabin.Infotainment.Media.DeclinedURI
   * VSS kind: sensor
   * VSS datatype: string
   * Description: URI of suggested media that was declined
   */
  attribute def Vehicle_Cabin_Infotainment_Media_DeclinedURI : String;

  /* VSS path: Vehicle.Cabin.Infotainment.Media.Played.Album
   * VSS kind: sensor
   * VSS datatype: string
   * Description: Name of album being played
   */
  attribute def Vehicle_Cabin_Infotainment_Media_Played_Album : String;

  /* VSS path: Vehicle.Cabin.Infotainment.Media.Played.Artist
   * VSS kind: sensor
   * VSS datatype: string
   * Description: Name of artist being played
   */
  attribute def Vehicle_Cabin_Infotainment_Media_Played_Artist : String;

  /* VSS path: Vehicle.Cabin.Infotainment.Media.Played.Genre
   * VSS kind: sensor
   * VSS datatype: string
   * Description: Name of genre being played
   */
  attribute def Vehicle_Cabin_Infotainment_Media_Played_Genre : String;

  /* VSS path: Vehicle.Cabin.Infotainment.Media.Played.PlaybackRate
   * VSS kind: actuator
   * VSS datatype: float
   * Description: Current playback rate of media being played.
   * Comment: The normal playback rate is multiplied by this value to obtain the current rate, so a value of 1.0 indicates normal speed. Values of lower than 1.0 make the media play slower than normal. Values of higher than 1.0 make the media play faster than normal.
   */
  attribute def Vehicle_Cabin_Infotainment_Media_Played_PlaybackRate : Real;

  /* VSS path: Vehicle.Cabin.Infotainment.Media.Played.Source
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Media selected for playback
   * Allowed values: ['UNKNOWN', 'SIRIUS_XM', 'AM', 'FM', 'DAB', 'TV', 'CD', 'DVD', 'AUX', 'USB', 'DISK', 'BLUETOOTH', 'INTERNET', 'VOICE', 'BEEP']
   */
  attribute def Vehicle_Cabin_Infotainment_Media_Played_Source : String;

  /* VSS path: Vehicle.Cabin.Infotainment.Media.Played.Track
   * VSS kind: sensor
   * VSS datatype: string
   * Description: Name of track being played
   */
  attribute def Vehicle_Cabin_Infotainment_Media_Played_Track : String;

  /* VSS path: Vehicle.Cabin.Infotainment.Media.Played.URI
   * VSS kind: sensor
   * VSS datatype: string
   * Description: User Resource associated with the media
   */
  attribute def Vehicle_Cabin_Infotainment_Media_Played_URI : String;

  /* VSS path: Vehicle.Cabin.Infotainment.Media.SelectedURI
   * VSS kind: actuator
   * VSS datatype: string
   * Description: URI of suggested media that was selected
   */
  attribute def Vehicle_Cabin_Infotainment_Media_SelectedURI : String;

  /* VSS path: Vehicle.Cabin.Infotainment.Media.Volume
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Current Media Volume
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Cabin_Infotainment_Media_Volume : Integer;

  /* VSS path: Vehicle.Cabin.Infotainment.Navigation.DestinationSet.Latitude
   * VSS kind: actuator
   * VSS datatype: double
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Latitude of destination in WGS 84 geodetic coordinates.
   * Value range: min=-90, max=90
   */
  attribute def Vehicle_Cabin_Infotainment_Navigation_DestinationSet_Latitude : Real;

  /* VSS path: Vehicle.Cabin.Infotainment.Navigation.DestinationSet.Longitude
   * VSS kind: actuator
   * VSS datatype: double
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Longitude of destination in WGS 84 geodetic coordinates.
   * Value range: min=-180, max=180
   */
  attribute def Vehicle_Cabin_Infotainment_Navigation_DestinationSet_Longitude : Real;

  /* VSS path: Vehicle.Cabin.Infotainment.Navigation.GuidanceVoice
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Navigation guidance state that was selected.
   * Comment: ETC indicates a voice alternative not covered by the explicitly listed alternatives.
   * Allowed values: ['STANDARD_MALE', 'STANDARD_FEMALE', 'ETC']
   */
  attribute def Vehicle_Cabin_Infotainment_Navigation_GuidanceVoice : String;

  /* VSS path: Vehicle.Cabin.Infotainment.Navigation.Map.IsAutoScaleModeUsed
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Used to select auto-scaling mode. This feature dynamically adjusts the zoom level of the map to provide an optimal view based on the current speed of the vehicle
   * Comment: If true, then auto-scaling mode is used. If false, then manual-scaling mode is used.
   */
  attribute def Vehicle_Cabin_Infotainment_Navigation_Map_IsAutoScaleModeUsed : Boolean;

  /* VSS path: Vehicle.Cabin.Infotainment.Navigation.Mute
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Navigation mute state that was selected.
   * Allowed values: ['MUTED', 'ALERT_ONLY', 'UNMUTED']
   */
  attribute def Vehicle_Cabin_Infotainment_Navigation_Mute : String;

  /* VSS path: Vehicle.Cabin.Infotainment.Navigation.Volume
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Current navigation volume
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Cabin_Infotainment_Navigation_Volume : Integer;

  /* VSS path: Vehicle.Cabin.Infotainment.PowerOptimizeLevel
   * VSS kind: actuator
   * VSS datatype: uint8
   * Description: Power optimization level for this branch/subsystem. A higher number indicates more aggressive power optimization. Level 0 indicates that all functionality is enabled, no power optimization enabled. Level 10 indicates most aggressive power optimization mode, only essential functionality enabled.
   * Value range: min=0, max=10
   */
  attribute def Vehicle_Cabin_Infotainment_PowerOptimizeLevel : Integer;

  /* VSS path: Vehicle.Cabin.Infotainment.SmartphoneProjection.Active
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Projection activation info.
   * Comment: NONE indicates that projection is not supported.
   * Allowed values: ['NONE', 'ACTIVE', 'INACTIVE']
   */
  attribute def Vehicle_Cabin_Infotainment_SmartphoneProjection_Active : String;

  /* VSS path: Vehicle.Cabin.Infotainment.SmartphoneProjection.Source
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Connectivity source selected for projection.
   * Comment: Smartphone projection exposes or controls specific applications on the Smartphone on the vehicle infotainment system.
   * Allowed values: ['USB', 'BLUETOOTH', 'WIFI']
   */
  attribute def Vehicle_Cabin_Infotainment_SmartphoneProjection_Source : String;

  /* VSS path: Vehicle.Cabin.Infotainment.SmartphoneProjection.SupportedMode
   * VSS kind: attribute
   * VSS datatype: string[]
   * Description: Supportable list for projection.
   * Allowed values: ['ANDROID_AUTO', 'APPLE_CARPLAY', 'MIRROR_LINK', 'OTHER']
   */
  attribute def Vehicle_Cabin_Infotainment_SmartphoneProjection_SupportedMode : String;

  /* VSS path: Vehicle.Cabin.Infotainment.SmartphoneScreenMirroring.Active
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Mirroring activation info.
   * Comment: NONE indicates that mirroring is not supported.
   * Allowed values: ['NONE', 'ACTIVE', 'INACTIVE']
   */
  attribute def Vehicle_Cabin_Infotainment_SmartphoneScreenMirroring_Active : String;

  /* VSS path: Vehicle.Cabin.Infotainment.SmartphoneScreenMirroring.Source
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Connectivity source selected for mirroring.
   * Allowed values: ['USB', 'BLUETOOTH', 'WIFI']
   */
  attribute def Vehicle_Cabin_Infotainment_SmartphoneScreenMirroring_Source : String;

  /* VSS path: Vehicle.Cabin.IsAutoPowerOptimize
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Auto Power Optimization Flag When set to 'true', the system enables automatic power optimization, dynamically adjusting the power optimization level based on runtime conditions or features managed by the OEM. When set to 'false', manual control of the power optimization level is allowed.
   */
  attribute def Vehicle_Cabin_IsAutoPowerOptimize : Boolean;

  /* VSS path: Vehicle.Cabin.IsWindowChildLockEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is window child lock engaged. True = Engaged. False = Disengaged.
   * Comment: Window child lock refers to the functionality to disable the move window button next to most windows, so that they only can be operated by the driver.
   */
  attribute def Vehicle_Cabin_IsWindowChildLockEngaged : Boolean;

  /* VSS path: Vehicle.Cabin.Light.AmbientLight.Color
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Hexadecimal color code represented as a 3-byte RGB (i.e. Red, Green, and Blue) value preceded by a hash symbol "#". Allowed range "#000000" to "#FFFFFF".
   * Comment: For example; "#C0C0C0" = Silver, "#FFD700" = Gold, "#000000" = Black, "#FFFFFF" = White, etc.
   */
  attribute def Vehicle_Cabin_Light_AmbientLight_Color : String;

  /* VSS path: Vehicle.Cabin.Light.AmbientLight.Intensity
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: How much of the maximum possible brightness of the light is used. 1 = Maximum attenuation, 100 = No attenuation (i.e. full brightness).
   * Comment: Minimum value cannot be zero as on/off is controlled by the actuator IsLightOn. V4.0 moved from Cabin.Lights.AmbientLight.Intensity to enable individual control of lights via the SingleConfigurableLight.vspec.
   * Value range: min=1, max=100
   */
  attribute def Vehicle_Cabin_Light_AmbientLight_Intensity : Integer;

  /* VSS path: Vehicle.Cabin.Light.AmbientLight.IsLightOn
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Indicates whether the light is turned on. True = On, False = Off.
   */
  attribute def Vehicle_Cabin_Light_AmbientLight_IsLightOn : Boolean;

  /* VSS path: Vehicle.Cabin.Light.InteractiveLightBar.Color
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Hexadecimal color code represented as a 3-byte RGB (i.e. Red, Green, and Blue) value preceded by a hash symbol "#". Allowed range "#000000" to "#FFFFFF".
   * Comment: For example; "#C0C0C0" = Silver, "#FFD700" = Gold, "#000000" = Black, "#FFFFFF" = White, etc.
   */
  attribute def Vehicle_Cabin_Light_InteractiveLightBar_Color : String;

  /* VSS path: Vehicle.Cabin.Light.InteractiveLightBar.Effect
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Light effect selection from a predefined set of allowed values.
   * Comment: Default and allowed values are OEM-specific and should be defined accordingly (e.g. with the use of overlays).
   */
  attribute def Vehicle_Cabin_Light_InteractiveLightBar_Effect : String;

  /* VSS path: Vehicle.Cabin.Light.InteractiveLightBar.Intensity
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: How much of the maximum possible brightness of the light is used. 1 = Maximum attenuation, 100 = No attenuation (i.e. full brightness).
   * Comment: Minimum value cannot be zero as on/off is controlled by the actuator IsLightOn. V4.0 moved from Cabin.Lights.AmbientLight.Intensity to enable individual control of lights via the SingleConfigurableLight.vspec.
   * Value range: min=1, max=100
   */
  attribute def Vehicle_Cabin_Light_InteractiveLightBar_Intensity : Integer;

  /* VSS path: Vehicle.Cabin.Light.InteractiveLightBar.IsLightOn
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Indicates whether the light is turned on. True = On, False = Off.
   */
  attribute def Vehicle_Cabin_Light_InteractiveLightBar_IsLightOn : Boolean;

  /* VSS path: Vehicle.Cabin.Light.IsDomeOn
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is central dome light on
   */
  attribute def Vehicle_Cabin_Light_IsDomeOn : Boolean;

  /* VSS path: Vehicle.Cabin.Light.IsGloveBoxOn
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is glove box light on
   */
  attribute def Vehicle_Cabin_Light_IsGloveBoxOn : Boolean;

  /* VSS path: Vehicle.Cabin.Light.PerceivedAmbientLight
   * VSS kind: sensor
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: The percentage of ambient light that is measured (e.g., by a sensor) inside the cabin. 0 = No ambient light. 100 = Full brightness.
   * Comment: V4.0 named changed from "AmbientLight" to "PerceivedAmbientLight". This is a read-only property that refers to the pre-existing light (e.g., natural light). If you are looking for the in-cabin decorative lights that sometimes are also called "AmbientLights", please refer to the branch Vehicle.Cabin.Light.AmbientLight.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Cabin_Light_PerceivedAmbientLight : Integer;

  /* VSS path: Vehicle.Cabin.Light.Spotlight.Color
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Hexadecimal color code represented as a 3-byte RGB (i.e. Red, Green, and Blue) value preceded by a hash symbol "#". Allowed range "#000000" to "#FFFFFF".
   * Comment: For example; "#C0C0C0" = Silver, "#FFD700" = Gold, "#000000" = Black, "#FFFFFF" = White, etc.
   */
  attribute def Vehicle_Cabin_Light_Spotlight_Color : String;

  /* VSS path: Vehicle.Cabin.Light.Spotlight.Intensity
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: How much of the maximum possible brightness of the light is used. 1 = Maximum attenuation, 100 = No attenuation (i.e. full brightness).
   * Comment: Minimum value cannot be zero as on/off is controlled by the actuator IsLightOn. V4.0 moved from Cabin.Lights.AmbientLight.Intensity to enable individual control of lights via the SingleConfigurableLight.vspec.
   * Value range: min=1, max=100
   */
  attribute def Vehicle_Cabin_Light_Spotlight_Intensity : Integer;

  /* VSS path: Vehicle.Cabin.Light.Spotlight.IsLightOn
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Indicates whether the light is turned on. True = On, False = Off.
   */
  attribute def Vehicle_Cabin_Light_Spotlight_IsLightOn : Boolean;

  /* VSS path: Vehicle.Cabin.PowerOptimizeLevel
   * VSS kind: actuator
   * VSS datatype: uint8
   * Description: Power optimization level for this branch/subsystem. A higher number indicates more aggressive power optimization. Level 0 indicates that all functionality is enabled, no power optimization enabled. Level 10 indicates most aggressive power optimization mode, only essential functionality enabled.
   * Value range: min=0, max=10
   */
  attribute def Vehicle_Cabin_PowerOptimizeLevel : Integer;

  /* VSS path: Vehicle.Cabin.RearShade.IsOpen
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is item open or closed? True = Fully or partially open. False = Fully closed.
   */
  attribute def Vehicle_Cabin_RearShade_IsOpen : Boolean;

  /* VSS path: Vehicle.Cabin.RearShade.Position
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Item position. 0 = Start position 100 = End position.
   * Comment: Relationship between Open/Close and Start/End position is item dependent.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Cabin_RearShade_Position : Integer;

  /* VSS path: Vehicle.Cabin.RearShade.Switch
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Switch controlling sliding action such as window, sunroof, or blind.
   * Allowed values: ['INACTIVE', 'CLOSE', 'OPEN', 'ONE_SHOT_CLOSE', 'ONE_SHOT_OPEN']
   */
  attribute def Vehicle_Cabin_RearShade_Switch : String;

  /* VSS path: Vehicle.Cabin.RearviewMirror.DimmingLevel
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Dimming level of rear-view mirror. 0 = Undimmed. 100 = Fully dimmed.
   * Value range: min=, max=100
   */
  attribute def Vehicle_Cabin_RearviewMirror_DimmingLevel : Integer;

  /* VSS path: Vehicle.Cabin.Seat.Airbag.IsDeployed
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Airbag deployment status. True = Airbag deployed. False = Airbag not deployed.
   */
  attribute def Vehicle_Cabin_Seat_Airbag_IsDeployed : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.Airbag.IsEnabled
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Airbag enabled status. True = Airbag enabled. False = Airbag not enabled.
   */
  attribute def Vehicle_Cabin_Seat_Airbag_IsEnabled : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.Backrest.BottomLumbarSupport
   * VSS kind: actuator
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Bottom lumbar support (in/out position). 0 = Innermost position. 100 = Outermost position.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Cabin_Seat_Backrest_BottomLumbarSupport : Real;

  /* VSS path: Vehicle.Cabin.Seat.Backrest.HeatingCooling
   * VSS kind: actuator
   * VSS datatype: int8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Heating or Cooling requsted for the Item. -100 = Maximum cooling, 0 = Heating/cooling deactivated, 100 = Maximum heating.
   * Value range: min=-100, max=100
   */
  attribute def Vehicle_Cabin_Seat_Backrest_HeatingCooling : Integer;

  /* VSS path: Vehicle.Cabin.Seat.Backrest.IsLessLumbarSupportSwitchEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is switch for less lumbar support engaged.
   * Comment: Affects the property (Backrest.LumbarSupport).
   */
  attribute def Vehicle_Cabin_Seat_Backrest_IsLessLumbarSupportSwitchEngaged : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.Backrest.IsLessSideBolsterSupportSwitchEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is switch for less side bolster support engaged.
   * Comment: Affects the property (Backrest.SideBolsterSupport).
   */
  attribute def Vehicle_Cabin_Seat_Backrest_IsLessSideBolsterSupportSwitchEngaged : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.Backrest.IsLumbarDownSwitchEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Lumbar down switch engaged.
   * Comment: Affects the property (Backrest.LumbarSupport).
   */
  attribute def Vehicle_Cabin_Seat_Backrest_IsLumbarDownSwitchEngaged : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.Backrest.IsLumbarUpSwitchEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Lumbar up switch engaged.
   * Comment: Affects the property (Backrest.LumbarSupport).
   */
  attribute def Vehicle_Cabin_Seat_Backrest_IsLumbarUpSwitchEngaged : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.Backrest.IsMoreLumbarSupportSwitchEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is switch for more lumbar support engaged.
   * Comment: Affects the property (Backrest.LumbarSupport).
   */
  attribute def Vehicle_Cabin_Seat_Backrest_IsMoreLumbarSupportSwitchEngaged : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.Backrest.IsMoreSideBolsterSupportSwitchEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is switch for more side bolster support engaged.
   * Comment: Affects the property (Backrest.SideBolsterSupport).
   */
  attribute def Vehicle_Cabin_Seat_Backrest_IsMoreSideBolsterSupportSwitchEngaged : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.Backrest.IsReclineBackwardSwitchEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Backrest recline backward switch engaged.
   * Comment: Affects the property (Backrest.Recline).
   */
  attribute def Vehicle_Cabin_Seat_Backrest_IsReclineBackwardSwitchEngaged : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.Backrest.IsReclineForwardSwitchEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Backrest recline forward switch engaged.
   * Comment: Affects the property (Backrest.Recline).
   */
  attribute def Vehicle_Cabin_Seat_Backrest_IsReclineForwardSwitchEngaged : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.Backrest.LumbarHeight
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: Height of lumbar support. Position is relative within available movable range of the lumbar support. 0 = Lowermost position supported.
   * Value range: min=0, max=
   */
  attribute def Vehicle_Cabin_Seat_Backrest_LumbarHeight : Integer;

  /* VSS path: Vehicle.Cabin.Seat.Backrest.LumbarSupport
   * VSS kind: actuator
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Lumbar support (in/out position). 0 = Innermost position. 100 = Outermost position.
   * Comment: A vehicle should typically either use this generic lumbar signal or the more specified top/mid/bottom signals.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Cabin_Seat_Backrest_LumbarSupport : Real;

  /* VSS path: Vehicle.Cabin.Seat.Backrest.MidLumbarSupport
   * VSS kind: actuator
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Mid lumbar support (in/out position). 0 = Innermost position. 100 = Outermost position.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Cabin_Seat_Backrest_MidLumbarSupport : Real;

  /* VSS path: Vehicle.Cabin.Seat.Backrest.Recline
   * VSS kind: actuator
   * VSS datatype: float
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Backrest recline compared to seat z-axis (seat vertical axis). 0 degrees = Upright/Vertical backrest. Negative degrees for forward recline. Positive degrees for backward recline.
   * Comment: Seat z-axis depends on seat tilt. This means that movement of backrest due to seat tilting will not affect Backrest.Recline as long as the angle between Seating and Backrest are constant. Absolute recline relative to vehicle z-axis can be calculated as Tilt + Backrest.Recline.
   */
  attribute def Vehicle_Cabin_Seat_Backrest_Recline : Real;

  /* VSS path: Vehicle.Cabin.Seat.Backrest.SideBolsterSupport
   * VSS kind: actuator
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Side bolster support. 0 = Minimum support (widest side bolster setting). 100 = Maximum support.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Cabin_Seat_Backrest_SideBolsterSupport : Real;

  /* VSS path: Vehicle.Cabin.Seat.Backrest.SideBolsterSupportLeft
   * VSS kind: actuator
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Side bolster support left. 0 = Minimum support (widest side bolster setting). 100 = Maximum support.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Cabin_Seat_Backrest_SideBolsterSupportLeft : Real;

  /* VSS path: Vehicle.Cabin.Seat.Backrest.SideBolsterSupportRight
   * VSS kind: actuator
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Side bolster support right. 0 = Minimum support (widest side bolster setting). 100 = Maximum support.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Cabin_Seat_Backrest_SideBolsterSupportRight : Real;

  /* VSS path: Vehicle.Cabin.Seat.Backrest.TopLumbarSupport
   * VSS kind: actuator
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Top lumbar support (in/out position). 0 = Innermost position. 100 = Outermost position.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Cabin_Seat_Backrest_TopLumbarSupport : Real;

  /* VSS path: Vehicle.Cabin.Seat.Backrest.UpperShoulderSupport
   * VSS kind: actuator
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Upper shoulder support. 0 = Minimum support (widest side bolster setting). 100 = Maximum support.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Cabin_Seat_Backrest_UpperShoulderSupport : Real;

  /* VSS path: Vehicle.Cabin.Seat.Headrest.Angle
   * VSS kind: actuator
   * VSS datatype: float
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Headrest angle, relative to backrest, 0 degrees if parallel to backrest, Positive degrees = tilted forward.
   */
  attribute def Vehicle_Cabin_Seat_Headrest_Angle : Real;

  /* VSS path: Vehicle.Cabin.Seat.Headrest.Height
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: Position of headrest relative to movable range of the head rest. 0 = Bottommost position supported.
   * Value range: min=0, max=
   */
  attribute def Vehicle_Cabin_Seat_Headrest_Height : Integer;

  /* VSS path: Vehicle.Cabin.Seat.Headrest.IsBackwardSwitchEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Headrest backward switch engaged.
   * Comment: Affects the property (Headrest.Angle).
   */
  attribute def Vehicle_Cabin_Seat_Headrest_IsBackwardSwitchEngaged : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.Headrest.IsDownSwitchEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Headrest down switch engaged.
   * Comment: Affects the property (Headrest.Height).
   */
  attribute def Vehicle_Cabin_Seat_Headrest_IsDownSwitchEngaged : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.Headrest.IsForwardSwitchEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Headrest forward switch engaged.
   * Comment: Affects the property (Headrest.Angle).
   */
  attribute def Vehicle_Cabin_Seat_Headrest_IsForwardSwitchEngaged : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.Headrest.IsUpSwitchEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Headrest up switch engaged.
   * Comment: Affects the property (Headrest.Height).
   */
  attribute def Vehicle_Cabin_Seat_Headrest_IsUpSwitchEngaged : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.HeatingCooling
   * VSS kind: actuator
   * VSS datatype: int8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Heating or Cooling requsted for the Item. -100 = Maximum cooling, 0 = Heating/cooling deactivated, 100 = Maximum heating.
   * Value range: min=-100, max=100
   */
  attribute def Vehicle_Cabin_Seat_HeatingCooling : Integer;

  /* VSS path: Vehicle.Cabin.Seat.Height
   * VSS kind: actuator
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: Seat position on vehicle z-axis. Position is relative within available movable range of the seating. 0 = Lowermost position supported.
   * Value range: min=0, max=
   */
  attribute def Vehicle_Cabin_Seat_Height : Integer;

  /* VSS path: Vehicle.Cabin.Seat.IsBackwardSwitchEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Seat backward switch engaged.
   * Comment: Affects the property (Position).
   */
  attribute def Vehicle_Cabin_Seat_IsBackwardSwitchEngaged : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.IsBelted
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Is the belt engaged.
   */
  attribute def Vehicle_Cabin_Seat_IsBelted : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.IsCoolerSwitchEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Cooler switch for Seat heater.
   * Comment: Affects the property (HeatingCooling).
   */
  attribute def Vehicle_Cabin_Seat_IsCoolerSwitchEngaged : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.IsDecreaseMassageLevelSwitchEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Decrease massage level switch engaged.
   * Comment: Affects the property (Massage.Level).
   */
  attribute def Vehicle_Cabin_Seat_IsDecreaseMassageLevelSwitchEngaged : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.IsDownSwitchEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Seat down switch engaged.
   * Comment: Affects the property (Height).
   */
  attribute def Vehicle_Cabin_Seat_IsDownSwitchEngaged : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.IsForwardSwitchEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Seat forward switch engaged.
   * Comment: Affects the property (Position).
   */
  attribute def Vehicle_Cabin_Seat_IsForwardSwitchEngaged : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.IsIncreaseMassageLevelSwitchEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Increase massage level switch engaged.
   * Comment: Affects the property (Massage.Level).
   */
  attribute def Vehicle_Cabin_Seat_IsIncreaseMassageLevelSwitchEngaged : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.IsTiltBackwardSwitchEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Tilt backward switch engaged.
   * Comment: Affects the property (Tilt).
   */
  attribute def Vehicle_Cabin_Seat_IsTiltBackwardSwitchEngaged : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.IsTiltForwardSwitchEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Tilt forward switch engaged.
   * Comment: Affects the property (Tilt).
   */
  attribute def Vehicle_Cabin_Seat_IsTiltForwardSwitchEngaged : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.IsUpSwitchEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Seat up switch engaged.
   * Comment: Affects the property (Height).
   */
  attribute def Vehicle_Cabin_Seat_IsUpSwitchEngaged : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.IsWarmerSwitchEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Warmer switch for Seat heater.
   * Comment: Affects the property (HeatingCooling).
   */
  attribute def Vehicle_Cabin_Seat_IsWarmerSwitchEngaged : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.Massage.IsAvailable
   * VSS kind: attribute
   * VSS datatype: boolean
   * Description: True if the seat have the massage capability
   */
  attribute def Vehicle_Cabin_Seat_Massage_IsAvailable : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.Massage.Level
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Seat massage level. 0 = off. 100 = max massage.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Cabin_Seat_Massage_Level : Integer;

  /* VSS path: Vehicle.Cabin.Seat.Massage.Status
   * VSS kind: sensor
   * VSS datatype: string
   * Description: Massage status.
   * Allowed values: ['ON', 'OFF']
   */
  attribute def Vehicle_Cabin_Seat_Massage_Status : String;

  /* VSS path: Vehicle.Cabin.Seat.Massage.SupportedTypes
   * VSS kind: attribute
   * VSS datatype: string[]
   * Description: Type of massage.
   * Comment: OEMs may define a list of identifiers for supported massage types using the allowed keyword
   */
  attribute def Vehicle_Cabin_Seat_Massage_SupportedTypes : String;

  /* VSS path: Vehicle.Cabin.Seat.Massage.TypeActive
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Type of massage active.
   * Comment: OEMs may define a list of identifiers for supported massage types using the allowed keyword
   */
  attribute def Vehicle_Cabin_Seat_Massage_TypeActive : String;

  /* VSS path: Vehicle.Cabin.Seat.NeckScarf.FanSpeed
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Speed of the fan.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Cabin_Seat_NeckScarf_FanSpeed : Integer;

  /* VSS path: Vehicle.Cabin.Seat.NeckScarf.HeatingCooling
   * VSS kind: actuator
   * VSS datatype: int8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Heating or Cooling requsted for the Item. -100 = Maximum cooling, 0 = Heating/cooling deactivated, 100 = Maximum heating.
   * Value range: min=-100, max=100
   */
  attribute def Vehicle_Cabin_Seat_NeckScarf_HeatingCooling : Integer;

  /* VSS path: Vehicle.Cabin.Seat.OccupancyStatus
   * VSS kind: sensor
   * VSS datatype: string
   * Description: Occupancy status of the seat.
   * Allowed values: ['UNKNOWN', 'OCCUPIED', 'EMPTY']
   */
  attribute def Vehicle_Cabin_Seat_OccupancyStatus : String;

  /* VSS path: Vehicle.Cabin.Seat.Position
   * VSS kind: actuator
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: Seat position on vehicle x-axis. Position is relative to the frontmost position supported by the seat. 0 = Frontmost position supported.
   * Value range: min=0, max=
   */
  attribute def Vehicle_Cabin_Seat_Position : Integer;

  /* VSS path: Vehicle.Cabin.Seat.SeatBeltHeight
   * VSS kind: actuator
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: Seat belt position on vehicle z-axis. Position is relative within available movable range of the seat belt. 0 = Lowermost position supported.
   */
  attribute def Vehicle_Cabin_Seat_SeatBeltHeight : Integer;

  /* VSS path: Vehicle.Cabin.Seat.Seating.HeatingCooling
   * VSS kind: actuator
   * VSS datatype: int8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Heating or Cooling requsted for the Item. -100 = Maximum cooling, 0 = Heating/cooling deactivated, 100 = Maximum heating.
   * Value range: min=-100, max=100
   */
  attribute def Vehicle_Cabin_Seat_Seating_HeatingCooling : Integer;

  /* VSS path: Vehicle.Cabin.Seat.Seating.IsBackwardSwitchEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is switch to decrease seating length engaged.
   * Comment: Affects the property (Seating.Length).
   */
  attribute def Vehicle_Cabin_Seat_Seating_IsBackwardSwitchEngaged : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.Seating.IsForwardSwitchEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is switch to increase seating length engaged.
   */
  attribute def Vehicle_Cabin_Seat_Seating_IsForwardSwitchEngaged : Boolean;

  /* VSS path: Vehicle.Cabin.Seat.Seating.Length
   * VSS kind: actuator
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: Length adjustment of seating. 0 = Adjustable part of seating in rearmost position (Shortest length of seating).
   * Value range: min=0, max=
   */
  attribute def Vehicle_Cabin_Seat_Seating_Length : Integer;

  /* VSS path: Vehicle.Cabin.Seat.Seating.SideBolsterSupportLeft
   * VSS kind: actuator
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Seat bottom side bolster support left. 0 = Minimum support (widest side bolster setting). 100 = Maximum support.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Cabin_Seat_Seating_SideBolsterSupportLeft : Real;

  /* VSS path: Vehicle.Cabin.Seat.Seating.SideBolsterSupportRight
   * VSS kind: actuator
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Seat bottom side bolster support right. 0 = Minimum support (widest side bolster setting). 100 = Maximum support.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Cabin_Seat_Seating_SideBolsterSupportRight : Real;

  /* VSS path: Vehicle.Cabin.Seat.Tilt
   * VSS kind: actuator
   * VSS datatype: float
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Tilting of seat (seating and backrest) relative to vehicle x-axis. 0 = seat bottom is flat, seat bottom and vehicle x-axis are parallel. Positive degrees = seat tilted backwards, seat x-axis tilted upward, seat z-axis is tilted backward.
   * Comment: In VSS it is assumed that tilting a seat affects both seating (seat bottom) and backrest, i.e. the angle between seating and backrest will not be affected when changing Tilt.
   */
  attribute def Vehicle_Cabin_Seat_Tilt : Real;

  /* VSS path: Vehicle.Cabin.SeatPosCount
   * VSS kind: attribute
   * VSS datatype: uint8[]
   * Description: Number of seats across each row from the front to the rear.
   * Comment: Default value corresponds to two seats in front row and 3 seats in second row.
   */
  attribute def Vehicle_Cabin_SeatPosCount : ScalarValues::ScalarValue;

  /* VSS path: Vehicle.Cabin.SeatRowCount
   * VSS kind: attribute
   * VSS datatype: uint8
   * Description: Number of seat rows in vehicle.
   * Comment: Default value corresponds to two rows of seats.
   */
  attribute def Vehicle_Cabin_SeatRowCount : Integer;

  /* VSS path: Vehicle.Cabin.Sunroof.Position
   * VSS kind: sensor
   * VSS datatype: int8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Sunroof position. 0 = Fully closed 100 = Fully opened. -100 = Fully tilted.
   * Value range: min=-100, max=100
   */
  attribute def Vehicle_Cabin_Sunroof_Position : Integer;

  /* VSS path: Vehicle.Cabin.Sunroof.Shade.IsOpen
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is item open or closed? True = Fully or partially open. False = Fully closed.
   */
  attribute def Vehicle_Cabin_Sunroof_Shade_IsOpen : Boolean;

  /* VSS path: Vehicle.Cabin.Sunroof.Shade.Position
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Item position. 0 = Start position 100 = End position.
   * Comment: Relationship between Open/Close and Start/End position is item dependent.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Cabin_Sunroof_Shade_Position : Integer;

  /* VSS path: Vehicle.Cabin.Sunroof.Shade.Switch
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Switch controlling sliding action such as window, sunroof, or blind.
   * Allowed values: ['INACTIVE', 'CLOSE', 'OPEN', 'ONE_SHOT_CLOSE', 'ONE_SHOT_OPEN']
   */
  attribute def Vehicle_Cabin_Sunroof_Shade_Switch : String;

  /* VSS path: Vehicle.Cabin.Sunroof.Switch
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Switch controlling sliding action such as window, sunroof, or shade.
   * Allowed values: ['INACTIVE', 'CLOSE', 'OPEN', 'ONE_SHOT_CLOSE', 'ONE_SHOT_OPEN', 'TILT_UP', 'TILT_DOWN']
   */
  attribute def Vehicle_Cabin_Sunroof_Switch : String;

  /* VSS path: Vehicle.CargoVolume
   * VSS kind: attribute
   * VSS datatype: float
   * Standard quantity reference: ISQ::volume
   * Standard unit reference: SI::litre
   * Description: The available volume for cargo or luggage. For automobiles, this is usually the trunk volume.
   * Value range: min=0, max=
   */
  attribute def Vehicle_CargoVolume : Real;

  /* VSS path: Vehicle.Chassis.Accelerator.PedalPosition
   * VSS kind: sensor
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Accelerator pedal position as percent. 0 = Not depressed. 100 = Fully depressed.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Chassis_Accelerator_PedalPosition : Integer;

  /* VSS path: Vehicle.Chassis.Axle.AxleWidth
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: The lateral distance between the wheel mounting faces, measured along the spindle axis.
   * Comment: Corresponds to SAE J1100-2009 W113.
   */
  attribute def Vehicle_Chassis_Axle_AxleWidth : Integer;

  /* VSS path: Vehicle.Chassis.Axle.SteeringAngle
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Single track two-axle model steering angle. Angle according to ISO 8855. Positive = degrees to the left. Negative = degrees to the right.
   * Comment: Single track two-axle model steering angle refers to the angle that a centrally mounted wheel would have.
   */
  attribute def Vehicle_Chassis_Axle_SteeringAngle : Real;

  /* VSS path: Vehicle.Chassis.Axle.TireAspectRatio
   * VSS kind: attribute
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Aspect ratio between tire section height and tire section width, as per ETRTO / TRA standard.
   */
  attribute def Vehicle_Chassis_Axle_TireAspectRatio : Integer;

  /* VSS path: Vehicle.Chassis.Axle.TireDiameter
   * VSS kind: attribute
   * VSS datatype: float
   * Standard quantity reference: ISQ::length
   * Standard unit reference: USCustomaryUnits::inch
   * Description: Outer diameter of tires, in inches, as per ETRTO / TRA standard.
   */
  attribute def Vehicle_Chassis_Axle_TireDiameter : Real;

  /* VSS path: Vehicle.Chassis.Axle.TireWidth
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: Nominal section width of tires, in mm, as per ETRTO / TRA standard.
   */
  attribute def Vehicle_Chassis_Axle_TireWidth : Integer;

  /* VSS path: Vehicle.Chassis.Axle.Torque
   * VSS kind: sensor
   * VSS datatype: int16
   * Standard quantity reference: ISQ::momentOfForce
   * Standard unit reference: SI::newtonMetre
   * Description: Incoming axle torque to differential. Negative values indicate regen mode.
   * Comment: For combustion engine this typically corresponds to the output torque of the multi-speed gearbox. For electrical motor this typically corresponds to the output torque of the single-speed reduction-gear. This signal is typically not used if there is separate electrical motors for left and right wheels.
   */
  attribute def Vehicle_Chassis_Axle_Torque : Integer;

  /* VSS path: Vehicle.Chassis.Axle.TrackWidth
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: The lateral distance between the centers of the wheels, measured along the spindle, or axle axis. If there are dual rear wheels, measure from the midway points between the inner and outer tires.
   * Comment: Corresponds to SAE J1100-2009 W102.
   */
  attribute def Vehicle_Chassis_Axle_TrackWidth : Integer;

  /* VSS path: Vehicle.Chassis.Axle.TreadWidth
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: The lateral distance between the centerlines of the base tires at ground, including camber angle. If there are dual rear wheels, measure from the midway points between the inner and outer tires.
   * Comment: Corresponds to SAE J1100-2009 W101.
   */
  attribute def Vehicle_Chassis_Axle_TreadWidth : Integer;

  /* VSS path: Vehicle.Chassis.Axle.Wheel.AngularSpeed
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::angularVelocity
   * Standard unit reference: SI::degreePerSecond
   * Description: Angular (Rotational) speed of a vehicle's wheel.
   * Comment: Positive if wheel is trying to drive vehicle forward. Negative if wheel is trying to drive vehicle backward.
   */
  attribute def Vehicle_Chassis_Axle_Wheel_AngularSpeed : Real;

  /* VSS path: Vehicle.Chassis.Axle.Wheel.Brake.FluidLevel
   * VSS kind: sensor
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Brake fluid level as percent. 0 = Empty. 100 = Full.
   * Value range: min=, max=100
   */
  attribute def Vehicle_Chassis_Axle_Wheel_Brake_FluidLevel : Integer;

  /* VSS path: Vehicle.Chassis.Axle.Wheel.Brake.IsBrakesWorn
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Brake pad wear status. True = Worn. False = Not Worn.
   */
  attribute def Vehicle_Chassis_Axle_Wheel_Brake_IsBrakesWorn : Boolean;

  /* VSS path: Vehicle.Chassis.Axle.Wheel.Brake.IsFluidLevelLow
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Brake fluid level status. True = Brake fluid level low. False = Brake fluid level OK.
   */
  attribute def Vehicle_Chassis_Axle_Wheel_Brake_IsFluidLevelLow : Boolean;

  /* VSS path: Vehicle.Chassis.Axle.Wheel.Brake.PadWear
   * VSS kind: sensor
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Brake pad wear as percent. 0 = No Wear. 100 = Worn.
   * Value range: min=, max=100
   */
  attribute def Vehicle_Chassis_Axle_Wheel_Brake_PadWear : Integer;

  /* VSS path: Vehicle.Chassis.Axle.Wheel.Speed
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::speed
   * Standard unit reference: SI::kilometrePerHour
   * Description: Linear speed of a vehicle's wheel.
   */
  attribute def Vehicle_Chassis_Axle_Wheel_Speed : Real;

  /* VSS path: Vehicle.Chassis.Axle.Wheel.Tire.AirTemperature
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::thermodynamicTemperature
   * Standard unit reference: SI::degreeCelsius
   * Description: Air temperature inside the tire in Celsius.
   */
  attribute def Vehicle_Chassis_Axle_Wheel_Tire_AirTemperature : Real;

  /* VSS path: Vehicle.Chassis.Axle.Wheel.Tire.IsPressureLow
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Tire Pressure Status. True = Low tire pressure. False = Good tire pressure.
   */
  attribute def Vehicle_Chassis_Axle_Wheel_Tire_IsPressureLow : Boolean;

  /* VSS path: Vehicle.Chassis.Axle.Wheel.Tire.Pressure
   * VSS kind: sensor
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::pressure
   * Standard unit reference: SI::kilopascal
   * Description: Tire pressure in kilo-Pascal.
   */
  attribute def Vehicle_Chassis_Axle_Wheel_Tire_Pressure : Integer;

  /* VSS path: Vehicle.Chassis.Axle.Wheel.Tire.RubberTemperature
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::thermodynamicTemperature
   * Standard unit reference: SI::degreeCelsius
   * Description: Rubber temperature of the tire in Celsius.
   */
  attribute def Vehicle_Chassis_Axle_Wheel_Tire_RubberTemperature : Real;

  /* VSS path: Vehicle.Chassis.Axle.Wheel.Tire.Temperature
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::thermodynamicTemperature
   * Standard unit reference: SI::degreeCelsius
   * Description: Tire temperature in Celsius.
   */
  attribute def Vehicle_Chassis_Axle_Wheel_Tire_Temperature : Real;

  /* VSS path: Vehicle.Chassis.Axle.Wheel.Torque
   * VSS kind: sensor
   * VSS datatype: int16
   * Standard quantity reference: ISQ::momentOfForce
   * Standard unit reference: SI::newtonMetre
   * Description: Torque provided by drivetrain, excluding torque provided by friction brakes. Negative values indicate regen mode.
   * Comment: This is typically the torque provided by the differential, or by a motor dedicated for this wheel, after reduction gear if present.
   */
  attribute def Vehicle_Chassis_Axle_Wheel_Torque : Integer;

  /* VSS path: Vehicle.Chassis.Axle.WheelCount
   * VSS kind: attribute
   * VSS datatype: uint8
   * Description: Number of wheels on the axle
   */
  attribute def Vehicle_Chassis_Axle_WheelCount : Integer;

  /* VSS path: Vehicle.Chassis.Axle.WheelDiameter
   * VSS kind: attribute
   * VSS datatype: float
   * Standard quantity reference: ISQ::length
   * Standard unit reference: USCustomaryUnits::inch
   * Description: Diameter of wheels (rims without tires), in inches, as per ETRTO / TRA standard.
   */
  attribute def Vehicle_Chassis_Axle_WheelDiameter : Real;

  /* VSS path: Vehicle.Chassis.Axle.WheelWidth
   * VSS kind: attribute
   * VSS datatype: float
   * Standard quantity reference: ISQ::length
   * Standard unit reference: USCustomaryUnits::inch
   * Description: Width of wheels (rims without tires), in inches, as per ETRTO / TRA standard.
   */
  attribute def Vehicle_Chassis_Axle_WheelWidth : Real;

  /* VSS path: Vehicle.Chassis.AxleCount
   * VSS kind: attribute
   * VSS datatype: uint8
   * Description: Number of axles on the vehicle
   */
  attribute def Vehicle_Chassis_AxleCount : Integer;

  /* VSS path: Vehicle.Chassis.Brake.IsDriverEmergencyBrakingDetected
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if emergency braking initiated by driver is detected. True = Emergency braking detected. False = Emergency braking not detected.
   * Comment: Detection of emergency braking can trigger Emergency Brake Assist (EBA) to engage.
   */
  attribute def Vehicle_Chassis_Brake_IsDriverEmergencyBrakingDetected : Boolean;

  /* VSS path: Vehicle.Chassis.Brake.PedalPosition
   * VSS kind: sensor
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Brake pedal position as percent. 0 = Not depressed. 100 = Fully depressed.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Chassis_Brake_PedalPosition : Integer;

  /* VSS path: Vehicle.Chassis.ParkingBrake.IsAutoApplyEnabled
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Indicates if parking brake will be automatically engaged when the vehicle engine is turned off.
   */
  attribute def Vehicle_Chassis_ParkingBrake_IsAutoApplyEnabled : Boolean;

  /* VSS path: Vehicle.Chassis.ParkingBrake.IsEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Parking brake status. True = Parking Brake is Engaged. False = Parking Brake is not Engaged.
   */
  attribute def Vehicle_Chassis_ParkingBrake_IsEngaged : Boolean;

  /* VSS path: Vehicle.Chassis.SteeringWheel.Angle
   * VSS kind: sensor
   * VSS datatype: int16
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Steering wheel angle. Positive = degrees to the left. Negative = degrees to the right.
   */
  attribute def Vehicle_Chassis_SteeringWheel_Angle : Integer;

  /* VSS path: Vehicle.Chassis.SteeringWheel.Extension
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Steering wheel column extension from dashboard. 0 = Closest to dashboard. 100 = Furthest from dashboard.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Chassis_SteeringWheel_Extension : Integer;

  /* VSS path: Vehicle.Chassis.SteeringWheel.HeatingCooling
   * VSS kind: actuator
   * VSS datatype: int8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Heating or Cooling requsted for the Item. -100 = Maximum cooling, 0 = Heating/cooling deactivated, 100 = Maximum heating.
   * Value range: min=-100, max=100
   */
  attribute def Vehicle_Chassis_SteeringWheel_HeatingCooling : Integer;

  /* VSS path: Vehicle.Chassis.SteeringWheel.Tilt
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Steering wheel column tilt. 0 = Lowest position. 100 = Highest position.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Chassis_SteeringWheel_Tilt : Integer;

  /* VSS path: Vehicle.Chassis.Wheelbase
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: Overall wheelbase, in mm.
   */
  attribute def Vehicle_Chassis_Wheelbase : Integer;

  /* VSS path: Vehicle.Connectivity.IsConnectivityAvailable
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if connectivity between vehicle and cloud is available. True = Connectivity is available. False = Connectivity is not available.
   * Comment: This signal can be used by onboard vehicle services to decide what features that shall be offered to the driver, for example disable the 'check for update' button if vehicle does not have connectivity.
   */
  attribute def Vehicle_Connectivity_IsConnectivityAvailable : Boolean;

  /* VSS path: Vehicle.ControlUnit.Health.Network.CAN.IsNetworkOK
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Network status. True = No network problems detected. False = Network problems detected.
   */
  attribute def Vehicle_ControlUnit_Health_Network_CAN_IsNetworkOK : Boolean;

  /* VSS path: Vehicle.ControlUnit.Health.Network.ETH.IsNetworkOK
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Network status. True = No network problems detected. False = Network problems detected.
   */
  attribute def Vehicle_ControlUnit_Health_Network_ETH_IsNetworkOK : Boolean;

  /* VSS path: Vehicle.ControlUnit.Health.Resources.Power
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::power
   * Standard unit reference: SI::watt
   * Description: Power consumption
   */
  attribute def Vehicle_ControlUnit_Health_Resources_Power : Real;

  /* VSS path: Vehicle.ControlUnit.Health.Resources.Temperature
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::thermodynamicTemperature
   * Standard unit reference: SI::degreeCelsius
   * Description: Instance temperature
   */
  attribute def Vehicle_ControlUnit_Health_Resources_Temperature : Real;

  /* VSS path: Vehicle.ControlUnit.Health.Resources.Utilization.CPU
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: CPU utilization
   * Value range: min=0, max=100
   */
  attribute def Vehicle_ControlUnit_Health_Resources_Utilization_CPU : Real;

  /* VSS path: Vehicle.ControlUnit.Health.Resources.Utilization.Memory
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Memory utilization
   * Value range: min=0, max=100
   */
  attribute def Vehicle_ControlUnit_Health_Resources_Utilization_Memory : Real;

  /* VSS path: Vehicle.ControlUnit.Health.SWSupervision.IsAliveTriggered
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Whether the alive supervision was triggered
   */
  attribute def Vehicle_ControlUnit_Health_SWSupervision_IsAliveTriggered : Boolean;

  /* VSS path: Vehicle.ControlUnit.Health.SWSupervision.IsDeadlineTriggered
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Whether the deadline supervision was triggered
   */
  attribute def Vehicle_ControlUnit_Health_SWSupervision_IsDeadlineTriggered : Boolean;

  /* VSS path: Vehicle.ControlUnit.Health.SWSupervision.IsLogicalTriggered
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Whether the logical supervision was triggered
   */
  attribute def Vehicle_ControlUnit_Health_SWSupervision_IsLogicalTriggered : Boolean;

  /* VSS path: Vehicle.ControlUnit.Health.SWSupervision.IsWatchdogTriggered
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Whether the watchdog deadline was triggered
   */
  attribute def Vehicle_ControlUnit_Health_SWSupervision_IsWatchdogTriggered : Boolean;

  /* VSS path: Vehicle.ControlUnit.ID
   * VSS kind: attribute
   * VSS datatype: uint8
   * Description: Control unit ID
   */
  attribute def Vehicle_ControlUnit_ID : Integer;

  /* VSS path: Vehicle.CurbWeight
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::mass
   * Standard unit reference: SI::kilogram
   * Description: Vehicle curb weight, including all liquids and full tank of fuel, but no cargo or passengers.
   */
  attribute def Vehicle_CurbWeight : Integer;

  /* VSS path: Vehicle.CurrentLocation.Altitude
   * VSS kind: sensor
   * VSS datatype: double
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::metre
   * Description: Current altitude relative to WGS 84 reference ellipsoid, as measured at the position of GNSS receiver antenna.
   */
  attribute def Vehicle_CurrentLocation_Altitude : Real;

  /* VSS path: Vehicle.CurrentLocation.GNSSReceiver.FixType
   * VSS kind: sensor
   * VSS datatype: string
   * Description: Fix status of GNSS receiver.
   * Allowed values: ['NONE', 'TWO_D', 'TWO_D_SATELLITE_BASED_AUGMENTATION', 'TWO_D_GROUND_BASED_AUGMENTATION', 'TWO_D_SATELLITE_AND_GROUND_BASED_AUGMENTATION', 'THREE_D', 'THREE_D_SATELLITE_BASED_AUGMENTATION', 'THREE_D_GROUND_BASED_AUGMENTATION', 'THREE_D_SATELLITE_AND_GROUND_BASED_AUGMENTATION']
   */
  attribute def Vehicle_CurrentLocation_GNSSReceiver_FixType : String;

  /* VSS path: Vehicle.CurrentLocation.GNSSReceiver.MountingPosition.X
   * VSS kind: attribute
   * VSS datatype: int16
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: Mounting position of GNSS receiver antenna relative to vehicle coordinate system. Axis definitions according to ISO 8855. Origin at center of (first) rear axle. Positive values = forward of rear axle. Negative values = backward of rear axle.
   */
  attribute def Vehicle_CurrentLocation_GNSSReceiver_MountingPosition_X : Integer;

  /* VSS path: Vehicle.CurrentLocation.GNSSReceiver.MountingPosition.Y
   * VSS kind: attribute
   * VSS datatype: int16
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: Mounting position of GNSS receiver antenna relative to vehicle coordinate system. Axis definitions according to ISO 8855. Origin at center of (first) rear axle. Positive values = left of origin. Negative values = right of origin. Left/Right is as seen from driver perspective, i.e. by a person looking forward.
   */
  attribute def Vehicle_CurrentLocation_GNSSReceiver_MountingPosition_Y : Integer;

  /* VSS path: Vehicle.CurrentLocation.GNSSReceiver.MountingPosition.Z
   * VSS kind: attribute
   * VSS datatype: int16
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: Mounting position of GNSS receiver on Z-axis. Axis definitions according to ISO 8855. Origin at center of (first) rear axle. Positive values = above center of rear axle. Negative values = below center of rear axle.
   */
  attribute def Vehicle_CurrentLocation_GNSSReceiver_MountingPosition_Z : Integer;

  /* VSS path: Vehicle.CurrentLocation.Heading
   * VSS kind: sensor
   * VSS datatype: double
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Current heading relative to geographic north. 0 = North, 90 = East, 180 = South, 270 = West.
   * Value range: min=0, max=360
   */
  attribute def Vehicle_CurrentLocation_Heading : Real;

  /* VSS path: Vehicle.CurrentLocation.HorizontalAccuracy
   * VSS kind: sensor
   * VSS datatype: double
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::metre
   * Description: Accuracy of the latitude and longitude coordinates.
   */
  attribute def Vehicle_CurrentLocation_HorizontalAccuracy : Real;

  /* VSS path: Vehicle.CurrentLocation.Latitude
   * VSS kind: sensor
   * VSS datatype: double
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Current latitude of vehicle in WGS 84 geodetic coordinates, as measured at the position of GNSS receiver antenna.
   * Value range: min=-90, max=90
   */
  attribute def Vehicle_CurrentLocation_Latitude : Real;

  /* VSS path: Vehicle.CurrentLocation.Longitude
   * VSS kind: sensor
   * VSS datatype: double
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Current longitude of vehicle in WGS 84 geodetic coordinates, as measured at the position of GNSS receiver antenna.
   * Value range: min=-180, max=180
   */
  attribute def Vehicle_CurrentLocation_Longitude : Real;

  /* VSS path: Vehicle.CurrentLocation.Timestamp
   * VSS kind: sensor
   * VSS datatype: string
   * Standard quantity reference: n/a
   * Standard unit reference: ISO 8601 lexical date/time string
   * Description: Timestamp from GNSS system for current location, formatted according to ISO 8601 with UTC time zone.
   */
  attribute def Vehicle_CurrentLocation_Timestamp : String;

  /* VSS path: Vehicle.CurrentLocation.VerticalAccuracy
   * VSS kind: sensor
   * VSS datatype: double
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::metre
   * Description: Accuracy of altitude.
   */
  attribute def Vehicle_CurrentLocation_VerticalAccuracy : Real;

  /* VSS path: Vehicle.CurrentOverallWeight
   * VSS kind: sensor
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::mass
   * Standard unit reference: SI::kilogram
   * Description: Current overall Vehicle weight. Including passengers, cargo and other load inside the car.
   */
  attribute def Vehicle_CurrentOverallWeight : Integer;

  /* VSS path: Vehicle.Diagnostics.DTCCount
   * VSS kind: sensor
   * VSS datatype: uint8
   * Description: Number of Diagnostic Trouble Codes (DTC)
   */
  attribute def Vehicle_Diagnostics_DTCCount : Integer;

  /* VSS path: Vehicle.Diagnostics.DTCList
   * VSS kind: sensor
   * VSS datatype: string[]
   * Description: List of currently active DTCs formatted according OBD II (SAE-J2012DA_201812) standard ([P|C|B|U]XXXXX )
   */
  attribute def Vehicle_Diagnostics_DTCList : String;

  /* VSS path: Vehicle.Driver.AttentiveProbability
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Probability of attentiveness of the driver.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Driver_AttentiveProbability : Real;

  /* VSS path: Vehicle.Driver.DistractionLevel
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Distraction level of the driver, which can be evaluated by multiple factors e.g. driving situation, acoustical or optical signals inside the cockpit, ongoing phone calls.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Driver_DistractionLevel : Real;

  /* VSS path: Vehicle.Driver.FatigueLevel
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Fatigue level of the driver, which can be evaluated by multiple factors e.g. trip time, behaviour of steering, eye status.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Driver_FatigueLevel : Real;

  /* VSS path: Vehicle.Driver.HeartRate
   * VSS kind: sensor
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::frequency
   * Standard unit reference: SI-derived beats/minute
   * Description: Heart rate of the driver.
   */
  attribute def Vehicle_Driver_HeartRate : Integer;

  /* VSS path: Vehicle.Driver.IsEyesOnRoad
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Has driver the eyes on road or not?
   */
  attribute def Vehicle_Driver_IsEyesOnRoad : Boolean;

  /* VSS path: Vehicle.Driver.IsHandsOnWheel
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Are the driver's hands on the steering wheel or not?
   */
  attribute def Vehicle_Driver_IsHandsOnWheel : Boolean;

  /* VSS path: Vehicle.EmissionsCO2
   * VSS kind: attribute
   * VSS datatype: int16
   * Standard quantity reference: ISQ::linearDensity
   * Standard unit reference: SI-derived gram/kilometre
   * Description: The CO2 emissions.
   */
  attribute def Vehicle_EmissionsCO2 : Integer;

  /* VSS path: Vehicle.Exterior.AirTemperature
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::thermodynamicTemperature
   * Standard unit reference: SI::degreeCelsius
   * Description: Air temperature outside the vehicle.
   */
  attribute def Vehicle_Exterior_AirTemperature : Real;

  /* VSS path: Vehicle.Exterior.Humidity
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Relative humidity outside the vehicle. 0 = Dry, 100 = Air fully saturated.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Exterior_Humidity : Real;

  /* VSS path: Vehicle.Exterior.LightIntensity
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Light intensity outside the vehicle. 0 = No light detected, 100 = Fully lit.
   * Comment: Mapping to physical units and calculation method is sensor specific.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Exterior_LightIntensity : Real;

  /* VSS path: Vehicle.Exterior.RoadSurfaceCondition
   * VSS kind: sensor
   * VSS datatype: string
   * Description: Assessed condition of the road surface beneath or ahead of the vehicle.
   * Comment: Determination method is implementation specific. May be derived from sensor fusion of Vehicle.ADAS.ESC.RoadFriction.MostProbable, Vehicle.Exterior.AirTemperature, Vehicle.Body.Raindetection.Intensity, and optional camera-based road surface classification. UNKNOWN shall be used when the system cannot assess the road surface condition. Primary consumers: navigation and ADAS safety systems. Related to VSS issue #877 (Connected Safety signals).
   * Allowed values: ['UNKNOWN', 'DRY', 'WET', 'SNOW', 'ICE', 'SLUSH', 'WET_ICE', 'LOOSE_GRAVEL']
   */
  attribute def Vehicle_Exterior_RoadSurfaceCondition : String;

  /* VSS path: Vehicle.GrossWeight
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::mass
   * Standard unit reference: SI::kilogram
   * Description: Curb weight of vehicle, including all liquids and full tank of fuel and full load of cargo and passengers.
   */
  attribute def Vehicle_GrossWeight : Integer;

  /* VSS path: Vehicle.Height
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: Overall vehicle height.
   */
  attribute def Vehicle_Height : Integer;

  /* VSS path: Vehicle.IsAutoPowerOptimize
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Auto Power Optimization Flag When set to 'true', the system enables automatic power optimization, dynamically adjusting the power optimization level based on runtime conditions or features managed by the OEM. When set to 'false', manual control of the power optimization level is allowed.
   */
  attribute def Vehicle_IsAutoPowerOptimize : Boolean;

  /* VSS path: Vehicle.IsBrokenDown
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Vehicle breakdown or any similar event causing vehicle to stop on the road, that might pose a risk to other road users. True = Vehicle broken down on the road, due to e.g. engine problems, flat tire, out of gas, brake problems. False = Vehicle not broken down.
   * Comment: Actual criteria and method used to decide if a vehicle is broken down is implementation specific.
   */
  attribute def Vehicle_IsBrokenDown : Boolean;

  /* VSS path: Vehicle.IsMoving
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates whether the vehicle is stationary or moving.
   */
  attribute def Vehicle_IsMoving : Boolean;

  /* VSS path: Vehicle.Length
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: Overall vehicle length.
   */
  attribute def Vehicle_Length : Integer;

  /* VSS path: Vehicle.LowVoltageBattery.CurrentCurrent
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::electricCurrent
   * Standard unit reference: SI::ampere
   * Description: Current current flowing in/out of the low voltage battery. Positive = Current flowing in to battery, e.g. during charging or driving. Negative = Current flowing out of battery, e.g. when using the battery to start a combustion engine.
   */
  attribute def Vehicle_LowVoltageBattery_CurrentCurrent : Real;

  /* VSS path: Vehicle.LowVoltageBattery.CurrentVoltage
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::electricPotential
   * Standard unit reference: SI::volt
   * Description: Current Voltage of the low voltage battery.
   */
  attribute def Vehicle_LowVoltageBattery_CurrentVoltage : Real;

  /* VSS path: Vehicle.LowVoltageBattery.NominalCapacity
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::electricCharge
   * Standard unit reference: SI::ampereHour
   * Description: Nominal capacity of the low voltage battery.
   */
  attribute def Vehicle_LowVoltageBattery_NominalCapacity : Integer;

  /* VSS path: Vehicle.LowVoltageBattery.NominalVoltage
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::electricPotential
   * Standard unit reference: SI::volt
   * Description: Nominal Voltage of the battery.
   * Comment: Nominal voltage typically refers to voltage of fully charged battery when delivering rated capacity.
   */
  attribute def Vehicle_LowVoltageBattery_NominalVoltage : Integer;

  /* VSS path: Vehicle.LowVoltageSystemState
   * VSS kind: sensor
   * VSS datatype: string
   * Description: State of the supply voltage of the control units (usually 12V).
   * Allowed values: ['UNDEFINED', 'LOCK', 'OFF', 'ACC', 'ON', 'START']
   */
  attribute def Vehicle_LowVoltageSystemState : String;

  /* VSS path: Vehicle.MaxTowBallWeight
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::mass
   * Standard unit reference: SI::kilogram
   * Description: Maximum vertical weight on the tow ball of a trailer.
   */
  attribute def Vehicle_MaxTowBallWeight : Integer;

  /* VSS path: Vehicle.MaxTowWeight
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::mass
   * Standard unit reference: SI::kilogram
   * Description: Maximum weight of trailer.
   */
  attribute def Vehicle_MaxTowWeight : Integer;

  /* VSS path: Vehicle.MotionManagement.Brake.Axle.TorqueDistributionFrictionRightMaximum
   * VSS kind: actuator
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Maximum distribution range of the friction brake request on the axle to the right wheel. 0% = Complete friction torque shall be shifted to the left wheel. 50% = At most 50% friction torque may be shifted to the right wheel. 100% = Complete friction torque may be shifted to the right wheel.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_MotionManagement_Brake_Axle_TorqueDistributionFrictionRightMaximum : Integer;

  /* VSS path: Vehicle.MotionManagement.Brake.Axle.TorqueDistributionFrictionRightMinimum
   * VSS kind: actuator
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Minimum distribution range of the friction brake request on the axle to the right wheel. 0% = Complete friction torque may be shifted to the left wheel. 50% = At least 50% friction torque shall be shifted to the right wheel. 100% = Complete friction torque shall be shifted to the right wheel.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_MotionManagement_Brake_Axle_TorqueDistributionFrictionRightMinimum : Integer;

  /* VSS path: Vehicle.MotionManagement.Brake.Axle.TorqueElectricMinimum
   * VSS kind: actuator
   * VSS datatype: int16
   * Standard quantity reference: ISQ::momentOfForce
   * Standard unit reference: SI::newtonMetre
   * Description: Limit for regenerative brake torque at given axle. Brake Torque < 0Nm.
   * Value range: min=, max=0
   */
  attribute def Vehicle_MotionManagement_Brake_Axle_TorqueElectricMinimum : Integer;

  /* VSS path: Vehicle.MotionManagement.Brake.Axle.TorqueFrictionDifferenceMaximum
   * VSS kind: actuator
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::momentOfForce
   * Standard unit reference: SI::newtonMetre
   * Description: Maximum absolute wheel torque difference between left and right wheel for friction brake.
   */
  attribute def Vehicle_MotionManagement_Brake_Axle_TorqueFrictionDifferenceMaximum : Integer;

  /* VSS path: Vehicle.MotionManagement.Brake.Axle.Wheel.OmegaLower
   * VSS kind: actuator
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::angularVelocity
   * Standard unit reference: SI::radianPerSecond
   * Description: Lower wheel speed limit request controlled by friction brake. ISO 8855 wheel-spin velocity.
   */
  attribute def Vehicle_MotionManagement_Brake_Axle_Wheel_OmegaLower : Integer;

  /* VSS path: Vehicle.MotionManagement.Brake.Axle.Wheel.OmegaUpper
   * VSS kind: actuator
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::angularVelocity
   * Standard unit reference: SI::radianPerSecond
   * Description: Upper wheel speed limit request controlled by friction brake. ISO 8855 wheel-spin velocity.
   */
  attribute def Vehicle_MotionManagement_Brake_Axle_Wheel_OmegaUpper : Integer;

  /* VSS path: Vehicle.MotionManagement.Brake.Axle.Wheel.Torque
   * VSS kind: sensor
   * VSS datatype: int16
   * Standard quantity reference: ISQ::momentOfForce
   * Standard unit reference: SI::newtonMetre
   * Description: Estimated friction brake torque. Brake Torque < 0Nm.
   * Value range: min=, max=0
   */
  attribute def Vehicle_MotionManagement_Brake_Axle_Wheel_Torque : Integer;

  /* VSS path: Vehicle.MotionManagement.Brake.Axle.Wheel.TorqueArbitrated
   * VSS kind: sensor
   * VSS datatype: int16
   * Standard quantity reference: ISQ::momentOfForce
   * Standard unit reference: SI::newtonMetre
   * Description: Brake system internally calculated friction brake torque target. Brake Torque < 0Nm.
   * Value range: min=, max=0
   */
  attribute def Vehicle_MotionManagement_Brake_Axle_Wheel_TorqueArbitrated : Integer;

  /* VSS path: Vehicle.MotionManagement.Brake.Axle.Wheel.TorqueFrictionMaximum
   * VSS kind: actuator
   * VSS datatype: int16
   * Standard quantity reference: ISQ::momentOfForce
   * Standard unit reference: SI::newtonMetre
   * Description: Maximum wheel torque request for friction brake. Brake Torque < 0Nm.
   * Value range: min=, max=0
   */
  attribute def Vehicle_MotionManagement_Brake_Axle_Wheel_TorqueFrictionMaximum : Integer;

  /* VSS path: Vehicle.MotionManagement.Brake.Axle.Wheel.TorqueFrictionMinimum
   * VSS kind: actuator
   * VSS datatype: int16
   * Standard quantity reference: ISQ::momentOfForce
   * Standard unit reference: SI::newtonMetre
   * Description: Minimum wheel torque request for friction brake. Brake Torque < 0Nm.
   * Value range: min=, max=0
   */
  attribute def Vehicle_MotionManagement_Brake_Axle_Wheel_TorqueFrictionMinimum : Integer;

  /* VSS path: Vehicle.MotionManagement.Brake.VehicleForceDistributionFrontMaximum
   * VSS kind: actuator
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Maximum distribution range request of FxWhlSum to front axle. 0% = Complete longitudinal brake force shall be shifted to rear axle. 50% = At most 50% shall be shifted to front axle. 100% = Complete longitudinal brake force may be shifted to front axle.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_MotionManagement_Brake_VehicleForceDistributionFrontMaximum : Integer;

  /* VSS path: Vehicle.MotionManagement.Brake.VehicleForceDistributionFrontMinimum
   * VSS kind: actuator
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Minimum distribution range request of FxWhlSum to front axle. 0% = Complete longitudinal brake force may be shifted to rear axle. 50% = At least 50% shall be shifted to front axle. 100% = Complete longitudinal brake force shall be shifted to front axle.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_MotionManagement_Brake_VehicleForceDistributionFrontMinimum : Integer;

  /* VSS path: Vehicle.MotionManagement.Brake.VehicleForceElectric
   * VSS kind: actuator
   * VSS datatype: int16
   * Standard quantity reference: ISQ::force
   * Standard unit reference: SI::newton
   * Description: Regenerative brake force request (FxWhlSum). Sum of all tyre longitudinal forces. Brake Force < 0N.
   * Value range: min=, max=0
   */
  attribute def Vehicle_MotionManagement_Brake_VehicleForceElectric : Integer;

  /* VSS path: Vehicle.MotionManagement.Brake.VehicleForceElectricMinimumArbitrated
   * VSS kind: sensor
   * VSS datatype: int16
   * Standard quantity reference: ISQ::force
   * Standard unit reference: SI::newton
   * Description: Brake system internally calculated regenerative force limit at vehicle level for eAxle actuation. Brake Force < 0N.
   * Value range: min=, max=0
   */
  attribute def Vehicle_MotionManagement_Brake_VehicleForceElectricMinimumArbitrated : Integer;

  /* VSS path: Vehicle.MotionManagement.Brake.VehicleForceMaximum
   * VSS kind: actuator
   * VSS datatype: int16
   * Standard quantity reference: ISQ::force
   * Standard unit reference: SI::newton
   * Description: Maximum longitudinal brake force request (FxWhlSum). Sum of all tyre longitudinal forces. Brake Force < 0N.
   * Value range: min=, max=0
   */
  attribute def Vehicle_MotionManagement_Brake_VehicleForceMaximum : Integer;

  /* VSS path: Vehicle.MotionManagement.ElectricAxle.RotationalSpeed
   * VSS kind: sensor
   * VSS datatype: int16
   * Standard quantity reference: ISQ::angularVelocity
   * Standard unit reference: SI-derived revolutionPerMinute
   * Description: Rotational speed for the specified axle, positive sign for rotation in forward direction, negative sign for rotation in backward direction.
   */
  attribute def Vehicle_MotionManagement_ElectricAxle_RotationalSpeed : Integer;

  /* VSS path: Vehicle.MotionManagement.ElectricAxle.RotationalSpeedMaximumLimit
   * VSS kind: actuator
   * VSS datatype: int16
   * Standard quantity reference: ISQ::angularVelocity
   * Standard unit reference: SI-derived revolutionPerMinute
   * Description: Maximum allowed axle rotational speed in torque control mode, positive sign for rotation in forward direction, negative sign for rotation in backward direction.
   */
  attribute def Vehicle_MotionManagement_ElectricAxle_RotationalSpeedMaximumLimit : Integer;

  /* VSS path: Vehicle.MotionManagement.ElectricAxle.RotationalSpeedMinimumLimit
   * VSS kind: actuator
   * VSS datatype: int16
   * Standard quantity reference: ISQ::angularVelocity
   * Standard unit reference: SI-derived revolutionPerMinute
   * Description: Minimum allowed axle rotational speed in torque control mode, positive sign for rotation in forward direction, negative sign for rotation in backward direction.
   */
  attribute def Vehicle_MotionManagement_ElectricAxle_RotationalSpeedMinimumLimit : Integer;

  /* VSS path: Vehicle.MotionManagement.ElectricAxle.RotationalSpeedTarget
   * VSS kind: actuator
   * VSS datatype: int16
   * Standard quantity reference: ISQ::angularVelocity
   * Standard unit reference: SI-derived revolutionPerMinute
   * Description: Target axle rotational speed in rotation speed control mode, positive sign for rotation in forward direction, negative sign for rotation in backward direction.
   */
  attribute def Vehicle_MotionManagement_ElectricAxle_RotationalSpeedTarget : Integer;

  /* VSS path: Vehicle.MotionManagement.ElectricAxle.Torque
   * VSS kind: sensor
   * VSS datatype: int16
   * Standard quantity reference: ISQ::momentOfForce
   * Standard unit reference: SI::newtonMetre
   * Description: Axle torque, positive sign for torque in forward direction, negative sign for torque in backward direction.
   */
  attribute def Vehicle_MotionManagement_ElectricAxle_Torque : Integer;

  /* VSS path: Vehicle.MotionManagement.ElectricAxle.TorqueMaximum
   * VSS kind: sensor
   * VSS datatype: int16
   * Standard quantity reference: ISQ::momentOfForce
   * Standard unit reference: SI::newtonMetre
   * Description: Maximum momentarily available eAxle torque, positive sign for torque in forward direction, negative sign for torque in backward direction.
   */
  attribute def Vehicle_MotionManagement_ElectricAxle_TorqueMaximum : Integer;

  /* VSS path: Vehicle.MotionManagement.ElectricAxle.TorqueMaximumLimit
   * VSS kind: actuator
   * VSS datatype: int16
   * Standard quantity reference: ISQ::momentOfForce
   * Standard unit reference: SI::newtonMetre
   * Description: Maximum allowed eAxle torque in rotation speed control mode, positive sign for torque in forward direction, negative sign unused.
   */
  attribute def Vehicle_MotionManagement_ElectricAxle_TorqueMaximumLimit : Integer;

  /* VSS path: Vehicle.MotionManagement.ElectricAxle.TorqueMinimum
   * VSS kind: sensor
   * VSS datatype: int16
   * Standard quantity reference: ISQ::momentOfForce
   * Standard unit reference: SI::newtonMetre
   * Description: Minimum momentarily available eAxle torque, positive sign for torque in forward direction, negative sign for torque in backward direction.
   */
  attribute def Vehicle_MotionManagement_ElectricAxle_TorqueMinimum : Integer;

  /* VSS path: Vehicle.MotionManagement.ElectricAxle.TorqueMinimumLimit
   * VSS kind: actuator
   * VSS datatype: int16
   * Standard quantity reference: ISQ::momentOfForce
   * Standard unit reference: SI::newtonMetre
   * Description: Minimum allowed axle torque in rotation speed control mode, positive sign unused, negative sign for torque in backward direction (ISO8855).
   */
  attribute def Vehicle_MotionManagement_ElectricAxle_TorqueMinimumLimit : Integer;

  /* VSS path: Vehicle.MotionManagement.ElectricAxle.TorqueTarget
   * VSS kind: actuator
   * VSS datatype: int16
   * Standard quantity reference: ISQ::momentOfForce
   * Standard unit reference: SI::newtonMetre
   * Description: Target axle torque in torque control mode, positive sign for torque in forward direction, negative sign for torque in backward direction (ISO8855).
   */
  attribute def Vehicle_MotionManagement_ElectricAxle_TorqueTarget : Integer;

  /* VSS path: Vehicle.MotionManagement.Steering.Axle.Row1.PositionOffsetTargetMode
   * VSS kind: actuator
   * VSS datatype: uint8
   * Description: Mode used for controlling position offset interface of axle steering actuator. 0 indicates interface disabled. Other values activate vehicle specific modes.
   */
  attribute def Vehicle_MotionManagement_Steering_Axle_Row1_PositionOffsetTargetMode : Integer;

  /* VSS path: Vehicle.MotionManagement.Steering.Axle.Row1.PositionTargetMode
   * VSS kind: actuator
   * VSS datatype: uint8
   * Description: Mode used for controlling position interface of axle steering actuator. 0 indicates interface disabled. Other values activate vehicle specific modes.
   */
  attribute def Vehicle_MotionManagement_Steering_Axle_Row1_PositionTargetMode : Integer;

  /* VSS path: Vehicle.MotionManagement.Steering.Axle.Row1.RackPosition
   * VSS kind: sensor
   * VSS datatype: int16
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: Represents the current position of the steering rack on axle steering actuator. Positive values leads to a left turn of the vehicle (based on ISO8855).
   * Comment: Alternative signal to SteerAngle.
   */
  attribute def Vehicle_MotionManagement_Steering_Axle_Row1_RackPosition : Integer;

  /* VSS path: Vehicle.MotionManagement.Steering.Axle.Row1.RackPositionOffsetTarget
   * VSS kind: actuator
   * VSS datatype: int16
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: Rack position offset request to the axle steering actuator (for steer-by-wire), added to the actuator internal calculated set-point. Positive values without internal calculated set point change lead to a left movement of the vehicle (based on ISO8855).
   * Comment: Alternative signal to SteerAngleOffsetTarget.
   */
  attribute def Vehicle_MotionManagement_Steering_Axle_Row1_RackPositionOffsetTarget : Integer;

  /* VSS path: Vehicle.MotionManagement.Steering.Axle.Row1.RackPositionTarget
   * VSS kind: actuator
   * VSS datatype: int16
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: Rack position request to the axle steering actuator (external set-point). Positive values lead to a left turn of the vehicle (based on ISO8855).
   * Comment: Alternative signal to SteerAngleTarget.
   */
  attribute def Vehicle_MotionManagement_Steering_Axle_Row1_RackPositionTarget : Integer;

  /* VSS path: Vehicle.MotionManagement.Steering.Axle.Row1.SteerAngle
   * VSS kind: sensor
   * VSS datatype: int16
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Represents the current actuated steering angle of the steered wheels. Signal orientation according ISO8855, single track model.
   * Comment: Alternative signal to RackPosition.
   */
  attribute def Vehicle_MotionManagement_Steering_Axle_Row1_SteerAngle : Integer;

  /* VSS path: Vehicle.MotionManagement.Steering.Axle.Row1.SteerAngleOffsetTarget
   * VSS kind: actuator
   * VSS datatype: int16
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Steer angle offset request to the axle steering actuator (for steer-by-wire), added to the actuator internal calculated set-point. Signal orientation according ISO8855, single track model.
   * Comment: Alternative signal to RackPositionOffsetTarget.
   */
  attribute def Vehicle_MotionManagement_Steering_Axle_Row1_SteerAngleOffsetTarget : Integer;

  /* VSS path: Vehicle.MotionManagement.Steering.Axle.Row1.SteerAngleTarget
   * VSS kind: actuator
   * VSS datatype: int16
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Steer angle request to the axle steering actuator (external set-point). Signal orientation according ISO8855, single track model.
   * Comment: Alternative signal to RackPositionTarget.
   */
  attribute def Vehicle_MotionManagement_Steering_Axle_Row1_SteerAngleTarget : Integer;

  /* VSS path: Vehicle.MotionManagement.Steering.Axle.Row2.SteerAngle
   * VSS kind: sensor
   * VSS datatype: int16
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Represents the current actuated steering angle of the steered wheels on rear axle. Signal orientation according ISO8855, single track model.
   */
  attribute def Vehicle_MotionManagement_Steering_Axle_Row2_SteerAngle : Integer;

  /* VSS path: Vehicle.MotionManagement.Steering.Axle.Row2.SteerAngleTarget
   * VSS kind: actuator
   * VSS datatype: int16
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Steer angle request to the rear axle steering actuator (external set-point). Signal orientation according ISO8855, single track model.
   */
  attribute def Vehicle_MotionManagement_Steering_Axle_Row2_SteerAngleTarget : Integer;

  /* VSS path: Vehicle.MotionManagement.Steering.Axle.Row2.SteerAngleVelocityTarget
   * VSS kind: actuator
   * VSS datatype: int16
   * Standard quantity reference: ISQ::angularVelocity
   * Standard unit reference: SI::degreePerSecond
   * Description: Requested velocity for steer angle change. Signal orientation according ISO8855. Optional signal to adapt rear wheel steering closed loop control gain.
   */
  attribute def Vehicle_MotionManagement_Steering_Axle_Row2_SteerAngleVelocityTarget : Integer;

  /* VSS path: Vehicle.MotionManagement.Steering.SteeringWheel.Angle
   * VSS kind: sensor
   * VSS datatype: int16
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Represents the current input angle of the steering system, typically corresponds to angle applied by driver on the steering-wheel. Positive for angle in counterclockwise direction (based on ISO8855).
   */
  attribute def Vehicle_MotionManagement_Steering_SteeringWheel_Angle : Integer;

  /* VSS path: Vehicle.MotionManagement.Steering.SteeringWheel.AngleTarget
   * VSS kind: actuator
   * VSS datatype: int16
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Steering-wheel angle request to the steering actuator (external set-point for steer-by-wire). Positive sign for angle in counterclockwise direction (based on ISO8855).
   */
  attribute def Vehicle_MotionManagement_Steering_SteeringWheel_AngleTarget : Integer;

  /* VSS path: Vehicle.MotionManagement.Steering.SteeringWheel.AngleTargetMode
   * VSS kind: actuator
   * VSS datatype: uint8
   * Description: Mode used for controlling Steering-wheel angle interface. 0 indicates interface disabled. Other values activate vehicle specific modes.
   */
  attribute def Vehicle_MotionManagement_Steering_SteeringWheel_AngleTargetMode : Integer;

  /* VSS path: Vehicle.MotionManagement.Steering.SteeringWheel.Torque
   * VSS kind: sensor
   * VSS datatype: int16
   * Standard quantity reference: ISQ::momentOfForce
   * Standard unit reference: SI::newtonMetre
   * Description: Represents the current input torque for steering system, typically corresponds to torque applied by driver on the steering wheel. Positive for torque in counterclockwise direction (based on ISO8855).
   */
  attribute def Vehicle_MotionManagement_Steering_SteeringWheel_Torque : Integer;

  /* VSS path: Vehicle.MotionManagement.Steering.SteeringWheel.TorqueOffsetTarget
   * VSS kind: actuator
   * VSS datatype: int16
   * Standard quantity reference: ISQ::momentOfForce
   * Standard unit reference: SI::newtonMetre
   * Description: Steering-wheel torque offset request to the steering actuator, added to the actuator internal calculated target value. Positive sign for torque in counterclockwise direction (based on ISO8855).
   */
  attribute def Vehicle_MotionManagement_Steering_SteeringWheel_TorqueOffsetTarget : Integer;

  /* VSS path: Vehicle.MotionManagement.Steering.SteeringWheel.TorqueOffsetTargetMode
   * VSS kind: actuator
   * VSS datatype: uint8
   * Description: Mode used for controlling steering-wheel torque offset interface. 0 indicates interface disabled. Other values activate vehicle specific modes.
   */
  attribute def Vehicle_MotionManagement_Steering_SteeringWheel_TorqueOffsetTargetMode : Integer;

  /* VSS path: Vehicle.MotionManagement.Steering.SteeringWheel.TorqueTarget
   * VSS kind: actuator
   * VSS datatype: int16
   * Standard quantity reference: ISQ::momentOfForce
   * Standard unit reference: SI::newtonMetre
   * Description: Steering-wheel torque request to the steering actuator (external set-point for steer-by-wire). Positive sign for torque in counterclockwise direction (based on ISO8855).
   */
  attribute def Vehicle_MotionManagement_Steering_SteeringWheel_TorqueTarget : Integer;

  /* VSS path: Vehicle.MotionManagement.Steering.SteeringWheel.TorqueTargetMode
   * VSS kind: actuator
   * VSS datatype: uint8
   * Description: Mode used for controlling Steering-wheel torque interface. 0 indicates interface disabled. Other values activate vehicle specific modes.
   */
  attribute def Vehicle_MotionManagement_Steering_SteeringWheel_TorqueTargetMode : Integer;

  /* VSS path: Vehicle.MotionManagement.Suspension.Axle.RollTorque
   * VSS kind: sensor
   * VSS datatype: int16
   * Standard quantity reference: ISQ::momentOfForce
   * Standard unit reference: SI::newtonMetre
   * Description: Actuated roll torque on this axle by anti-roll actuator. Signal orientation according to ISO8855.
   */
  attribute def Vehicle_MotionManagement_Suspension_Axle_RollTorque : Integer;

  /* VSS path: Vehicle.MotionManagement.Suspension.Axle.Wheel.DampingForce
   * VSS kind: sensor
   * VSS datatype: int16
   * Standard quantity reference: ISQ::force
   * Standard unit reference: SI::newton
   * Description: Actuated damping force at given wheel. Signal orientation according ISO8855, meaning positive force is pointing upwards.
   * Comment: Alternative signal to DampingRate.
   */
  attribute def Vehicle_MotionManagement_Suspension_Axle_Wheel_DampingForce : Integer;

  /* VSS path: Vehicle.MotionManagement.Suspension.Axle.Wheel.DampingForceTarget
   * VSS kind: actuator
   * VSS datatype: int16
   * Standard quantity reference: ISQ::force
   * Standard unit reference: SI::newton
   * Description: Damping force request at given wheel. Signal orientation according ISO8855, meaning positive force is pointing upwards.
   * Comment: Alternative signal to DampingRateTarget.
   */
  attribute def Vehicle_MotionManagement_Suspension_Axle_Wheel_DampingForceTarget : Integer;

  /* VSS path: Vehicle.MotionManagement.Suspension.Axle.Wheel.DampingRate
   * VSS kind: sensor
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Actuated damping rate at given wheel. 0% = lowest possible damping rate 100% = highest possible damping rate
   * Comment: Alternative signal to DampingForce.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_MotionManagement_Suspension_Axle_Wheel_DampingRate : Integer;

  /* VSS path: Vehicle.MotionManagement.Suspension.Axle.Wheel.DampingRateTarget
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Damping rate request at given wheel. 0% = lowest possible damping rate 100% = highest possible damping rate
   * Comment: Alternative signal to DampingForceTarget.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_MotionManagement_Suspension_Axle_Wheel_DampingRateTarget : Integer;

  /* VSS path: Vehicle.MotionManagement.Suspension.DampingPrioTarget
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Prioritization target for damping control 0% = damping control by damping actuator (e.g. base functions) 100% = damping control by VMM system (e.g. vehicle dynamics)
   * Value range: min=0, max=100
   */
  attribute def Vehicle_MotionManagement_Suspension_DampingPrioTarget : Integer;

  /* VSS path: Vehicle.MotionManagement.Suspension.RollPrioTarget
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Prioritization target for anti-roll control 0% = anti-roll control by anti-roll actuator (e.g. base function) 100% = anti-roll control by VMM system (e.g. vehicle dynamics)
   * Value range: min=0, max=100
   */
  attribute def Vehicle_MotionManagement_Suspension_RollPrioTarget : Integer;

  /* VSS path: Vehicle.MotionManagement.Suspension.RollTorqueDistributionFrontMaximum
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Maximum distribution range request of roll torque to front axle. 0% = Complete roll torque shall be shifted to rear axle 100% = Complete roll torque may be shifted to front axle
   * Value range: min=0, max=100
   */
  attribute def Vehicle_MotionManagement_Suspension_RollTorqueDistributionFrontMaximum : Integer;

  /* VSS path: Vehicle.MotionManagement.Suspension.RollTorqueDistributionFrontMinimum
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Minimum distribution range request of roll torque to front axle. 0% = Complete roll torque may be shifted to rear axle 100% = Complete roll torque shall be shifted to front axle
   * Value range: min=0, max=100
   */
  attribute def Vehicle_MotionManagement_Suspension_RollTorqueDistributionFrontMinimum : Integer;

  /* VSS path: Vehicle.MotionManagement.Suspension.RollTorqueTarget
   * VSS kind: actuator
   * VSS datatype: int16
   * Standard quantity reference: ISQ::momentOfForce
   * Standard unit reference: SI::newtonMetre
   * Description: Roll torque request on vehicle level. Signal orientation according to ISO8855.
   */
  attribute def Vehicle_MotionManagement_Suspension_RollTorqueTarget : Integer;

  /* VSS path: Vehicle.Occupant.HeadPosition.Pitch
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Head pitch angle, measured as angle from vehicle sprung mass XY-plane as defined by ISO 23150:2023 to the head X-axis. 0 = Head in normal position. Positive values = Head leaning up. Negative values = Head leaning down.
   * Value range: min=-90, max=90
   */
  attribute def Vehicle_Occupant_HeadPosition_Pitch : Real;

  /* VSS path: Vehicle.Occupant.HeadPosition.Roll
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Head roll angle about the head X-axis (right-hand rule). 0 = Head in normal position. Positive values = Head leaning to the right. Negative values = Head leaning to the left.
   * Value range: min=-180, max=180
   */
  attribute def Vehicle_Occupant_HeadPosition_Roll : Real;

  /* VSS path: Vehicle.Occupant.HeadPosition.X
   * VSS kind: sensor
   * VSS datatype: int16
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: Longitudinal position of head center measured as mid eye position on X-axis of the vehicle rear-axle coordinate system as defined by ISO 23150:2023 section 3.7.12 Mid eye position refers to the center of a line drawn between the center of the drivers eyes. Positive values = forward of (first) rear-axle. Negative values = backward of (first) rear-axle.
   */
  attribute def Vehicle_Occupant_HeadPosition_X : Integer;

  /* VSS path: Vehicle.Occupant.HeadPosition.Y
   * VSS kind: sensor
   * VSS datatype: int16
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: Lateral position of head center measured as mid eye position on X-axis of the vehicle rear-axle coordinate system as defined by ISO 23150:2023 section 3.7.12 Mid eye position refers to the center of a line drawn between the center of the drivers eyes. Positive values = left of rear-axle center. Negative values = right of rear-axle center.
   */
  attribute def Vehicle_Occupant_HeadPosition_Y : Integer;

  /* VSS path: Vehicle.Occupant.HeadPosition.Yaw
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Head yaw angle, measured from the vehicle sprung mass X-axis as defined by ISO 23150:2023 to the head X-axis, around the vehicle Z-axis (right-hand rule). 0 = Head in normal position. Positive values = Head turned left. Negative values = Head turned right.
   * Value range: min=-180, max=180
   */
  attribute def Vehicle_Occupant_HeadPosition_Yaw : Real;

  /* VSS path: Vehicle.Occupant.HeadPosition.Z
   * VSS kind: sensor
   * VSS datatype: int16
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: Height position of head center measured as mid eye position on X-axis of the vehicle rear-axle coordinate system as defined by ISO 23150:2023 section 3.7.12 Mid eye position refers to the center of a line drawn between the center of the drivers eyes. Positive values = above center of rear-axle reference point. Negative values = below center of rear-axle reference point.
   */
  attribute def Vehicle_Occupant_HeadPosition_Z : Integer;

  /* VSS path: Vehicle.Occupant.Identifier.Issuer
   * VSS kind: sensor
   * VSS datatype: string
   * Description: Unique Issuer for the authentication of the occupant e.g. https://accounts.funcorp.com.
   */
  attribute def Vehicle_Occupant_Identifier_Issuer : String;

  /* VSS path: Vehicle.Occupant.Identifier.Subject
   * VSS kind: sensor
   * VSS datatype: string
   * Description: Subject for the authentication of the occupant e.g. UserID 7331677.
   */
  attribute def Vehicle_Occupant_Identifier_Subject : String;

  /* VSS path: Vehicle.Occupant.MidEyeGaze.Azimuth
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Mid eye azimuth gaze (right-hand rule) on vehicle sprung mass Z-axis as defined by ISO 23150:2023 0 = Driver looking forward. Positive values = Driver looking at something on the left side of driver. Negative values = Driver looking at something on the right side of driver.
   * Value range: min=-180, max=180
   */
  attribute def Vehicle_Occupant_MidEyeGaze_Azimuth : Real;

  /* VSS path: Vehicle.Occupant.MidEyeGaze.Elevation
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Elevation to observed object measured as angle between vehicle sprung mass XY-plane as defined by ISO 23150:2023 at driver mid eye position and object. 0 = Driver looking at something at same height as mid eye position. Positive values = Driver looking at something above mid eye position. Negative values = Driver looking at something below mid eye position.
   * Value range: min=-90, max=90
   */
  attribute def Vehicle_Occupant_MidEyeGaze_Elevation : Real;

  /* VSS path: Vehicle.Orientation.Pitch
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Vehicle rotation (tilt) around Y (lateral). Positive values = nose up.
   * Comment: Reference is the vehicle at rest on a level surface. Useful for incline detection and trailer loading applications. Related to VSS issue #877 (Connected Safety signals).
   * Value range: min=-180, max=180
   */
  attribute def Vehicle_Orientation_Pitch : Real;

  /* VSS path: Vehicle.Orientation.Roll
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Vehicle rotation (tilt) around X (longitudinal). Positive values = right side down.
   * Comment: Reference is the vehicle at rest on a level surface. Useful for rollover detection and off-road applications. Related to VSS issue #877 (Connected Safety signals).
   * Value range: min=-180, max=180
   */
  attribute def Vehicle_Orientation_Roll : Real;

  /* VSS path: Vehicle.Orientation.Yaw
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Vehicle rotation around Z (vertical) relative to geographic north.
   * Comment: 0 = North, 90 = East, 180 = South, 270 = West. Complements CurrentLocation.Heading by providing IMU-derived orientation rather than GNSS-derived heading. Related to VSS issue #877 (Connected Safety signals).
   * Value range: min=0, max=360
   */
  attribute def Vehicle_Orientation_Yaw : Real;

  /* VSS path: Vehicle.PowerOptimizeLevel
   * VSS kind: actuator
   * VSS datatype: uint8
   * Description: Power optimization level for this branch/subsystem. A higher number indicates more aggressive power optimization. Level 0 indicates that all functionality is enabled, no power optimization enabled. Level 10 indicates most aggressive power optimization mode, only essential functionality enabled.
   * Value range: min=0, max=10
   */
  attribute def Vehicle_PowerOptimizeLevel : Integer;

  /* VSS path: Vehicle.Powertrain.AccumulatedBrakingEnergy
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::energy
   * Standard unit reference: SI::kilowattHour
   * Description: The accumulated energy from regenerative braking over lifetime.
   */
  attribute def Vehicle_Powertrain_AccumulatedBrakingEnergy : Real;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.AspirationType
   * VSS kind: attribute
   * VSS datatype: string
   * Description: Type of aspiration (natural, turbocharger, supercharger etc).
   * Allowed values: ['UNKNOWN', 'NATURAL', 'SUPERCHARGER', 'TURBOCHARGER']
   */
  attribute def Vehicle_Powertrain_CombustionEngine_AspirationType : String;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.Bore
   * VSS kind: attribute
   * VSS datatype: float
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: Bore in millimetres.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_Bore : Real;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.CompressionRatio
   * VSS kind: attribute
   * VSS datatype: string
   * Description: Engine compression ratio, specified in the format 'X:1', e.g. '9.2:1'.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_CompressionRatio : String;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.Configuration
   * VSS kind: attribute
   * VSS datatype: string
   * Description: Engine configuration.
   * Allowed values: ['UNKNOWN', 'STRAIGHT', 'V', 'BOXER', 'W', 'ROTARY', 'RADIAL', 'SQUARE', 'H', 'U', 'OPPOSED', 'X']
   */
  attribute def Vehicle_Powertrain_CombustionEngine_Configuration : String;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.DieselExhaustFluid.Capacity
   * VSS kind: attribute
   * VSS datatype: float
   * Standard quantity reference: ISQ::volume
   * Standard unit reference: SI::litre
   * Description: Capacity in liters of the Diesel Exhaust Fluid Tank.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_DieselExhaustFluid_Capacity : Real;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.DieselExhaustFluid.IsLevelLow
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if the Diesel Exhaust Fluid level is low. True if level is low. Definition of low is vehicle dependent.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_DieselExhaustFluid_IsLevelLow : Boolean;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.DieselExhaustFluid.Level
   * VSS kind: sensor
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Level of the Diesel Exhaust Fluid tank as percent of capacity. 0 = empty. 100 = full.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Powertrain_CombustionEngine_DieselExhaustFluid_Level : Integer;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.DieselExhaustFluid.Range
   * VSS kind: sensor
   * VSS datatype: uint32
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::metre
   * Description: Remaining range in meters of the Diesel Exhaust Fluid present in the vehicle.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_DieselExhaustFluid_Range : Integer;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.DieselParticulateFilter.DeltaPressure
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::pressure
   * Standard unit reference: SI::pascal
   * Description: Delta Pressure of Diesel Particulate Filter.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_DieselParticulateFilter_DeltaPressure : Real;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.DieselParticulateFilter.InletTemperature
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::thermodynamicTemperature
   * Standard unit reference: SI::degreeCelsius
   * Description: Inlet temperature of Diesel Particulate Filter.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_DieselParticulateFilter_InletTemperature : Real;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.DieselParticulateFilter.OutletTemperature
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::thermodynamicTemperature
   * Standard unit reference: SI::degreeCelsius
   * Description: Outlet temperature of Diesel Particulate Filter.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_DieselParticulateFilter_OutletTemperature : Real;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.Displacement
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::volume
   * Standard unit reference: SI::cubicCentimetre
   * Description: Displacement in cubic centimetres.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_Displacement : Integer;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.EOP
   * VSS kind: sensor
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::pressure
   * Standard unit reference: SI::kilopascal
   * Description: Engine oil pressure.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_EOP : Integer;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.EngineCode
   * VSS kind: attribute
   * VSS datatype: string
   * Description: Engine code designation, as specified by vehicle manufacturer.
   * Comment: For hybrid vehicles the engine code may refer to the combination of combustion and electric engine.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_EngineCode : String;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.EngineCoolant.Capacity
   * VSS kind: attribute
   * VSS datatype: float
   * Standard quantity reference: ISQ::volume
   * Standard unit reference: SI::litre
   * Description: Engine coolant capacity in liters.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_EngineCoolant_Capacity : Real;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.EngineCoolant.Level
   * VSS kind: sensor
   * VSS datatype: string
   * Description: Engine coolant level.
   * Allowed values: ['CRITICALLY_LOW', 'LOW', 'NORMAL']
   */
  attribute def Vehicle_Powertrain_CombustionEngine_EngineCoolant_Level : String;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.EngineCoolant.LifeRemaining
   * VSS kind: sensor
   * VSS datatype: int32
   * Standard quantity reference: ISQ::time
   * Standard unit reference: SI::second
   * Description: Remaining engine coolant life in seconds. Negative values can be used to indicate that lifetime has been exceeded.
   * Comment: In addition to this a signal a vehicle can report remaining time to service (including e.g. coolant change) by Vehicle.Service.TimeToService.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_EngineCoolant_LifeRemaining : Integer;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.EngineCoolant.Temperature
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::thermodynamicTemperature
   * Standard unit reference: SI::degreeCelsius
   * Description: Engine coolant temperature.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_EngineCoolant_Temperature : Real;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.EngineHours
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::time
   * Standard unit reference: SI::hour
   * Description: Accumulated time during engine lifetime with 'engine speed (rpm) > 0'.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_EngineHours : Real;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.EngineOil.Capacity
   * VSS kind: attribute
   * VSS datatype: float
   * Standard quantity reference: ISQ::volume
   * Standard unit reference: SI::litre
   * Description: Engine oil capacity in liters.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_EngineOil_Capacity : Real;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.EngineOil.Level
   * VSS kind: sensor
   * VSS datatype: string
   * Description: Engine oil level.
   * Allowed values: ['CRITICALLY_LOW', 'LOW', 'NORMAL', 'HIGH', 'CRITICALLY_HIGH']
   */
  attribute def Vehicle_Powertrain_CombustionEngine_EngineOil_Level : String;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.EngineOil.LifeRemaining
   * VSS kind: sensor
   * VSS datatype: int32
   * Standard quantity reference: ISQ::time
   * Standard unit reference: SI::second
   * Description: Remaining engine oil life in seconds. Negative values can be used to indicate that lifetime has been exceeded.
   * Comment: In addition to this a signal a vehicle can report remaining time to service (including e.g. oil change) by Vehicle.Service.TimeToService.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_EngineOil_LifeRemaining : Integer;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.EngineOil.PressureStatus
   * VSS kind: sensor
   * VSS datatype: string
   * Description: Engine oil pressure status.
   * Allowed values: ['NORMAL', 'WARNING', 'ALERT', 'ERROR']
   */
  attribute def Vehicle_Powertrain_CombustionEngine_EngineOil_PressureStatus : String;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.EngineOil.Temperature
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::thermodynamicTemperature
   * Standard unit reference: SI::degreeCelsius
   * Description: EOT, Engine oil temperature.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_EngineOil_Temperature : Real;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.IdleHours
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::time
   * Standard unit reference: SI::hour
   * Description: Accumulated idling time during engine lifetime. Definition of idling is not standardized.
   * Comment: Vehicles may calculate accumulated idle time for an engine. It might be based on engine speed (rpm) below a certain limit or any other mechanism.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_IdleHours : Real;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.IsRunning
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Engine Running. True if engine is rotating (Speed > 0).
   */
  attribute def Vehicle_Powertrain_CombustionEngine_IsRunning : Boolean;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.MAF
   * VSS kind: sensor
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::massFlowRate
   * Standard unit reference: SI::gramPerSecond
   * Description: Grams of air drawn into engine per second.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_MAF : Integer;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.MAP
   * VSS kind: sensor
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::pressure
   * Standard unit reference: SI::kilopascal
   * Description: Manifold absolute pressure possibly boosted using forced induction.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_MAP : Integer;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.MaxPower
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::power
   * Standard unit reference: SI::kilowatt
   * Description: Peak power, in kilowatts, that engine can generate.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_MaxPower : Integer;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.MaxTorque
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::momentOfForce
   * Standard unit reference: SI::newtonMetre
   * Description: Peak torque, in newton meter, that the engine can generate.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_MaxTorque : Integer;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.NumberOfCylinders
   * VSS kind: attribute
   * VSS datatype: uint16
   * Description: Number of cylinders.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_NumberOfCylinders : Integer;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.NumberOfValvesPerCylinder
   * VSS kind: attribute
   * VSS datatype: uint16
   * Description: Number of valves per cylinder.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_NumberOfValvesPerCylinder : Integer;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.Power
   * VSS kind: sensor
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::power
   * Standard unit reference: SI::kilowatt
   * Description: Current engine power output. Shall be reported as 0 during engine breaking.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_Power : Integer;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.Speed
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::angularVelocity
   * Standard unit reference: SI-derived revolutionPerMinute
   * Description: Engine speed measured as rotations per minute.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_Speed : Real;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.StrokeLength
   * VSS kind: attribute
   * VSS datatype: float
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: Stroke length in millimetres.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_StrokeLength : Real;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.TPS
   * VSS kind: sensor
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Current throttle position.
   * Value range: min=, max=100
   */
  attribute def Vehicle_Powertrain_CombustionEngine_TPS : Integer;

  /* VSS path: Vehicle.Powertrain.CombustionEngine.Torque
   * VSS kind: sensor
   * VSS datatype: int16
   * Standard quantity reference: ISQ::momentOfForce
   * Standard unit reference: SI::newtonMetre
   * Description: Current engine torque. Shall be reported as a negative number during engine breaking.
   * Comment: During engine breaking the engine delivers a negative torque to the transmission.
   */
  attribute def Vehicle_Powertrain_CombustionEngine_Torque : Integer;

  /* VSS path: Vehicle.Powertrain.ElectricMotor.EngineCode
   * VSS kind: attribute
   * VSS datatype: string
   * Description: Engine code designation, as specified by vehicle manufacturer.
   */
  attribute def Vehicle_Powertrain_ElectricMotor_EngineCode : String;

  /* VSS path: Vehicle.Powertrain.ElectricMotor.EngineCoolant.Capacity
   * VSS kind: attribute
   * VSS datatype: float
   * Standard quantity reference: ISQ::volume
   * Standard unit reference: SI::litre
   * Description: Engine coolant capacity in liters.
   */
  attribute def Vehicle_Powertrain_ElectricMotor_EngineCoolant_Capacity : Real;

  /* VSS path: Vehicle.Powertrain.ElectricMotor.EngineCoolant.Level
   * VSS kind: sensor
   * VSS datatype: string
   * Description: Engine coolant level.
   * Allowed values: ['CRITICALLY_LOW', 'LOW', 'NORMAL']
   */
  attribute def Vehicle_Powertrain_ElectricMotor_EngineCoolant_Level : String;

  /* VSS path: Vehicle.Powertrain.ElectricMotor.EngineCoolant.LifeRemaining
   * VSS kind: sensor
   * VSS datatype: int32
   * Standard quantity reference: ISQ::time
   * Standard unit reference: SI::second
   * Description: Remaining engine coolant life in seconds. Negative values can be used to indicate that lifetime has been exceeded.
   * Comment: In addition to this a signal a vehicle can report remaining time to service (including e.g. coolant change) by Vehicle.Service.TimeToService.
   */
  attribute def Vehicle_Powertrain_ElectricMotor_EngineCoolant_LifeRemaining : Integer;

  /* VSS path: Vehicle.Powertrain.ElectricMotor.EngineCoolant.Temperature
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::thermodynamicTemperature
   * Standard unit reference: SI::degreeCelsius
   * Description: Engine coolant temperature.
   */
  attribute def Vehicle_Powertrain_ElectricMotor_EngineCoolant_Temperature : Real;

  /* VSS path: Vehicle.Powertrain.ElectricMotor.MaxPower
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::power
   * Standard unit reference: SI::kilowatt
   * Description: Peak power, in kilowatts, that motor(s) can generate.
   */
  attribute def Vehicle_Powertrain_ElectricMotor_MaxPower : Integer;

  /* VSS path: Vehicle.Powertrain.ElectricMotor.MaxRegenPower
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::power
   * Standard unit reference: SI::kilowatt
   * Description: Peak regen/brake power, in kilowatts, that motor(s) can generate.
   */
  attribute def Vehicle_Powertrain_ElectricMotor_MaxRegenPower : Integer;

  /* VSS path: Vehicle.Powertrain.ElectricMotor.MaxRegenTorque
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::momentOfForce
   * Standard unit reference: SI::newtonMetre
   * Description: Peak regen/brake torque, in newton meter, that the motor(s) can generate.
   */
  attribute def Vehicle_Powertrain_ElectricMotor_MaxRegenTorque : Integer;

  /* VSS path: Vehicle.Powertrain.ElectricMotor.MaxTorque
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::momentOfForce
   * Standard unit reference: SI::newtonMetre
   * Description: Peak power, in newton meter, that the motor(s) can generate.
   */
  attribute def Vehicle_Powertrain_ElectricMotor_MaxTorque : Integer;

  /* VSS path: Vehicle.Powertrain.ElectricMotor.Power
   * VSS kind: sensor
   * VSS datatype: int16
   * Standard quantity reference: ISQ::power
   * Standard unit reference: SI::kilowatt
   * Description: Current motor power output. Negative values indicate regen mode.
   */
  attribute def Vehicle_Powertrain_ElectricMotor_Power : Integer;

  /* VSS path: Vehicle.Powertrain.ElectricMotor.Speed
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::angularVelocity
   * Standard unit reference: SI-derived revolutionPerMinute
   * Description: Motor rotational speed measured as rotations per minute. Negative values indicate reverse driving mode.
   */
  attribute def Vehicle_Powertrain_ElectricMotor_Speed : Real;

  /* VSS path: Vehicle.Powertrain.ElectricMotor.Temperature
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::thermodynamicTemperature
   * Standard unit reference: SI::degreeCelsius
   * Description: Motor temperature.
   */
  attribute def Vehicle_Powertrain_ElectricMotor_Temperature : Real;

  /* VSS path: Vehicle.Powertrain.ElectricMotor.TimeInUse
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::time
   * Standard unit reference: SI::hour
   * Description: Accumulated time during engine lifetime when the vehicule state's is 'READY'.
   * Comment: Vehicles may define their READY state.
   */
  attribute def Vehicle_Powertrain_ElectricMotor_TimeInUse : Real;

  /* VSS path: Vehicle.Powertrain.ElectricMotor.Torque
   * VSS kind: sensor
   * VSS datatype: int16
   * Standard quantity reference: ISQ::momentOfForce
   * Standard unit reference: SI::newtonMetre
   * Description: Current motor torque. Negative values indicate regen mode.
   */
  attribute def Vehicle_Powertrain_ElectricMotor_Torque : Integer;

  /* VSS path: Vehicle.Powertrain.FuelSystem.AbsoluteLevel
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::volume
   * Standard unit reference: SI::litre
   * Description: Current available fuel in the fuel tank expressed in liters.
   */
  attribute def Vehicle_Powertrain_FuelSystem_AbsoluteLevel : Real;

  /* VSS path: Vehicle.Powertrain.FuelSystem.AfterRefuelingFuelEconomy
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::fuelEfficiency
   * Standard unit reference: SI-derived kilometre/litre
   * Description: Average fuel economy calculated from the most recent refueling event to the current time.
   * Comment: This value represents the fuel efficiency for the period between consecutive refueling events. It is automatically reset to zero when refueling is detected and begins accumulating from that point. The calculation continues until the next refueling occurs. This metric is useful for tracking fuel efficiency improvements or changes between fill-ups.
   */
  attribute def Vehicle_Powertrain_FuelSystem_AfterRefuelingFuelEconomy : Real;

  /* VSS path: Vehicle.Powertrain.FuelSystem.AverageConsumption
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::fuelConsumption
   * Standard unit reference: SI-derived litrePer100Kilometre
   * Description: Average consumption in liters per 100 km.
   * Value range: min=0, max=
   */
  attribute def Vehicle_Powertrain_FuelSystem_AverageConsumption : Real;

  /* VSS path: Vehicle.Powertrain.FuelSystem.ConsumptionSinceLastRefuel
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::volume
   * Standard unit reference: SI::litre
   * Description: Fuel consumption since last refueling.
   * Comment: Amount of fuel consumed since last refueling.
   */
  attribute def Vehicle_Powertrain_FuelSystem_ConsumptionSinceLastRefuel : Real;

  /* VSS path: Vehicle.Powertrain.FuelSystem.ConsumptionSinceStart
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::volume
   * Standard unit reference: SI::litre
   * Description: Fuel amount in liters consumed since start of current trip.
   * Comment: A new trip is considered to start when engine gets enabled (e.g. LowVoltageSystemState in ON or START mode). A trip is considered to end when engine is no longer enabled. The signal may however keep the value of the last trip until a new trip is started.
   */
  attribute def Vehicle_Powertrain_FuelSystem_ConsumptionSinceStart : Real;

  /* VSS path: Vehicle.Powertrain.FuelSystem.CumulativeFuelEconomy
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::fuelEfficiency
   * Standard unit reference: SI-derived kilometre/litre
   * Description: Cumulative average fuel economy calculated from vehicle start or last user reset.
   * Comment: This represents the accumulated fuel economy over the entire period since the last reset. Unlike trip-based measurements, this provides a long-term average of fuel efficiency.
   */
  attribute def Vehicle_Powertrain_FuelSystem_CumulativeFuelEconomy : Real;

  /* VSS path: Vehicle.Powertrain.FuelSystem.DriveFuelEconomy
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::fuelEfficiency
   * Standard unit reference: SI-derived kilometre/litre
   * Description: Average fuel economy for the current drive cycle, calculated from engine start to current time.
   * Comment: This represents the fuel efficiency during the active driving session. The value is reset when the engine is no longer enabled or when the user manually initiates a drive fuel economy reset. After reset, it is recalculated from zero when the engine restarts or the new drive cycle begins. It provides real-time average fuel economy for the ongoing drive cycle.
   */
  attribute def Vehicle_Powertrain_FuelSystem_DriveFuelEconomy : Real;

  /* VSS path: Vehicle.Powertrain.FuelSystem.HybridType
   * VSS kind: attribute
   * VSS datatype: string
   * Description: Defines the hybrid type of the vehicle.
   * Allowed values: ['UNKNOWN', 'NOT_APPLICABLE', 'STOP_START', 'BELT_ISG', 'CIMG', 'PHEV']
   */
  attribute def Vehicle_Powertrain_FuelSystem_HybridType : String;

  /* VSS path: Vehicle.Powertrain.FuelSystem.InstantConsumption
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::fuelConsumption
   * Standard unit reference: SI-derived litrePer100Kilometre
   * Description: Current consumption in liters per 100 km.
   * Value range: min=0, max=
   */
  attribute def Vehicle_Powertrain_FuelSystem_InstantConsumption : Real;

  /* VSS path: Vehicle.Powertrain.FuelSystem.InstantantFuelEconomy
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::fuelEfficiency
   * Standard unit reference: SI-derived kilometre/litre
   * Description: Real-time instantaneous fuel economy calculated over a short time window.
   * Comment: This value represents the current fuel efficiency at any given moment during vehicle operation. It is calculated based on the distance traveled and fuel consumed over a brief sampling period (typically around 500ms). The calculation compares the vehicle state before and after the sampling window to determine instantaneous efficiency. This metric refreshes frequently and can fluctuate significantly based on driving conditions, acceleration, and terrain. Unlike average fuel economy measurements, this provides immediate feedback on current driving efficiency.
   */
  attribute def Vehicle_Powertrain_FuelSystem_InstantantFuelEconomy : Real;

  /* VSS path: Vehicle.Powertrain.FuelSystem.IsEngineStopStartEnabled
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates whether eco start stop is currently enabled.
   */
  attribute def Vehicle_Powertrain_FuelSystem_IsEngineStopStartEnabled : Boolean;

  /* VSS path: Vehicle.Powertrain.FuelSystem.IsFuelLevelEmpty
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates that the fuel gauge on the instrument cluster displays empty (0).
   * Comment: When this signal is true, the fuel gauge displays empty (0), but the vehicle typically still has reserve fuel allowing for some additional driving range depending on the vehicle design. This represents the displayed empty state, not actual tank empty condition.
   */
  attribute def Vehicle_Powertrain_FuelSystem_IsFuelLevelEmpty : Boolean;

  /* VSS path: Vehicle.Powertrain.FuelSystem.IsFuelLevelLow
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates that the fuel level is low (e.g. <50km range).
   */
  attribute def Vehicle_Powertrain_FuelSystem_IsFuelLevelLow : Boolean;

  /* VSS path: Vehicle.Powertrain.FuelSystem.IsFuelPortFlapOpen
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Status of the fuel port flap(s). True if at least one is open.
   */
  attribute def Vehicle_Powertrain_FuelSystem_IsFuelPortFlapOpen : Boolean;

  /* VSS path: Vehicle.Powertrain.FuelSystem.Range
   * VSS kind: sensor
   * VSS datatype: uint32
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::metre
   * Description: Remaining range in meters using only liquid fuel.
   */
  attribute def Vehicle_Powertrain_FuelSystem_Range : Integer;

  /* VSS path: Vehicle.Powertrain.FuelSystem.RefuelPortPosition
   * VSS kind: attribute
   * VSS datatype: string[]
   * Description: Position of refuel port(s). First part indicates side of vehicle, second part relative position on that side.
   * Allowed values: ['FRONT_LEFT', 'FRONT_MIDDLE', 'FRONT_RIGHT', 'REAR_LEFT', 'REAR_MIDDLE', 'REAR_RIGHT', 'LEFT_FRONT', 'LEFT_MIDDLE', 'LEFT_REAR', 'RIGHT_FRONT', 'RIGHT_MIDDLE', 'RIGHT_REAR']
   */
  attribute def Vehicle_Powertrain_FuelSystem_RefuelPortPosition : String;

  /* VSS path: Vehicle.Powertrain.FuelSystem.RelativeLevel
   * VSS kind: sensor
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Level in fuel tank as percent of capacity. 0 = empty. 100 = full.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Powertrain_FuelSystem_RelativeLevel : Integer;

  /* VSS path: Vehicle.Powertrain.FuelSystem.SupportedFuel
   * VSS kind: attribute
   * VSS datatype: string[]
   * Description: Detailed information on fuels supported by the vehicle. Identifiers originating from DIN EN 16942:2021-08, appendix B, with additional suffix for octane (RON) where relevant.
   * Comment: RON 95 is sometimes referred to as Super, RON 98 as Super Plus.
   * Allowed values: ['E5_95', 'E5_98', 'E10_95', 'E10_98', 'E85', 'B7', 'B10', 'B20', 'B30', 'B100', 'XTL', 'LPG', 'CNG', 'LNG', 'H2', 'OTHER']
   */
  attribute def Vehicle_Powertrain_FuelSystem_SupportedFuel : String;

  /* VSS path: Vehicle.Powertrain.FuelSystem.SupportedFuelTypes
   * VSS kind: attribute
   * VSS datatype: string[]
   * Description: High level information of fuel types supported
   * Comment: If a vehicle also has an electric drivetrain (e.g. hybrid) that will be obvious from the PowerTrain.Type signal.
   * Allowed values: ['GASOLINE', 'DIESEL', 'E85', 'LPG', 'CNG', 'LNG', 'H2', 'OTHER']
   */
  attribute def Vehicle_Powertrain_FuelSystem_SupportedFuelTypes : String;

  /* VSS path: Vehicle.Powertrain.FuelSystem.TankCapacity
   * VSS kind: attribute
   * VSS datatype: float
   * Standard quantity reference: ISQ::volume
   * Standard unit reference: SI::litre
   * Description: Capacity of the fuel tank in liters.
   */
  attribute def Vehicle_Powertrain_FuelSystem_TankCapacity : Real;

  /* VSS path: Vehicle.Powertrain.FuelSystem.TimeRemaining
   * VSS kind: sensor
   * VSS datatype: uint32
   * Standard quantity reference: ISQ::time
   * Standard unit reference: SI::second
   * Description: Time remaining in seconds before the fuel tank is empty.
   */
  attribute def Vehicle_Powertrain_FuelSystem_TimeRemaining : Integer;

  /* VSS path: Vehicle.Powertrain.IsAutoPowerOptimize
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Auto Power Optimization Flag When set to 'true', the system enables automatic power optimization, dynamically adjusting the power optimization level based on runtime conditions or features managed by the OEM. When set to 'false', manual control of the power optimization level is allowed.
   */
  attribute def Vehicle_Powertrain_IsAutoPowerOptimize : Boolean;

  /* VSS path: Vehicle.Powertrain.PowerOptimizeLevel
   * VSS kind: actuator
   * VSS datatype: uint8
   * Description: Power optimization level for this branch/subsystem. A higher number indicates more aggressive power optimization. Level 0 indicates that all functionality is enabled, no power optimization enabled. Level 10 indicates most aggressive power optimization mode, only essential functionality enabled.
   * Value range: min=0, max=10
   */
  attribute def Vehicle_Powertrain_PowerOptimizeLevel : Integer;

  /* VSS path: Vehicle.Powertrain.Range
   * VSS kind: sensor
   * VSS datatype: uint32
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::metre
   * Description: Remaining range in meters using all energy sources available in the vehicle.
   */
  attribute def Vehicle_Powertrain_Range : Integer;

  /* VSS path: Vehicle.Powertrain.RangeExtender.ChargeDepleting.EnergyConsumption
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::energyPerDistance
   * Standard unit reference: SI-derived kilowattHourPer100Kilometre
   * Description: Current electric energy consumption rate during Charge Depleting mode operation.
   * Comment: This value represents the instantaneous or short-term average electric energy consumption while the vehicle is operating in CD mode. It is calculated based on the electrical energy drawn from the traction battery per distance traveled. This metric is analogous to fuel consumption but measured in electrical energy units. A lower value indicates more efficient electric operation.
   */
  attribute def Vehicle_Powertrain_RangeExtender_ChargeDepleting_EnergyConsumption : Real;

  /* VSS path: Vehicle.Powertrain.RangeExtender.ChargeDepleting.Range
   * VSS kind: sensor
   * VSS datatype: uint32
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::metre
   * Description: Estimated remaining distance that can be traveled in Charge Depleting mode using available battery energy.
   * Comment: This range estimate is calculated based on the current battery state of charge and the recent energy consumption patterns in CD mode. The estimate may vary based on driving conditions, terrain, climate control usage, and other factors affecting battery consumption. When this range approaches zero, the vehicle will typically transition to Charge Sustaining mode.
   */
  attribute def Vehicle_Powertrain_RangeExtender_ChargeDepleting_Range : Integer;

  /* VSS path: Vehicle.Powertrain.RangeExtender.ChargeSustaining.FuelEconomy
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::fuelEfficiency
   * Standard unit reference: SI-derived kilometre/litre
   * Description: Current fuel economy during Charge Sustaining mode operation.
   * Comment: This value represents the fuel efficiency when the engine is operating as a generator to maintain battery charge. It differs from conventional vehicle fuel economy because the engine is optimized to run at efficient generator speeds rather than varying speeds for direct wheel propulsion. The actual fuel economy in CS mode may be different from the vehicle's rated CS mode fuel economy depending on driving conditions and power demands.
   */
  attribute def Vehicle_Powertrain_RangeExtender_ChargeSustaining_FuelEconomy : Real;

  /* VSS path: Vehicle.Powertrain.RangeExtender.ChargeSustaining.Range
   * VSS kind: sensor
   * VSS datatype: uint32
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::metre
   * Description: Estimated remaining distance that can be traveled in Charge Sustaining mode using available fuel.
   * Comment: This range estimate is calculated based on the current fuel level and recent fuel consumption patterns in CS mode. It represents the extended range capability provided by the internal combustion engine. The total vehicle range is the sum of CD mode range and CS mode range.
   */
  attribute def Vehicle_Powertrain_RangeExtender_ChargeSustaining_Range : Integer;

  /* VSS path: Vehicle.Powertrain.RangeExtender.CombinedFuelEconomy
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::fuelEfficiency
   * Standard unit reference: SI-derived kilometre/litre
   * Description: Combined fuel economy equivalent that accounts for both electric energy and fuel consumption.
   * Comment: This metric provides a unified measure of overall vehicle efficiency by converting electric energy consumption to a fuel-equivalent value and combining it with actual fuel consumption. The calculation typically follows regulatory standards (such as EPA MPGe) that define the equivalence between electrical energy and liquid fuel energy. For example, EPA defines 33.7 kWh as equivalent to one gallon of gasoline. This combined metric is useful for comparing EREV efficiency with conventional vehicles and understanding the overall energy cost of operation. The value is weighted based on the proportion of driving in CD versus CS modes.
   */
  attribute def Vehicle_Powertrain_RangeExtender_CombinedFuelEconomy : Real;

  /* VSS path: Vehicle.Powertrain.RangeExtender.OperatingMode
   * VSS kind: sensor
   * VSS datatype: string
   * Description: Current operating mode of the Extended Range Electric Vehicle.
   * Comment: CHARGE_DEPLETING (CD) - Vehicle operates primarily on battery power, battery SOC decreases. CHARGE_SUSTAINING (CS) - Engine operates as generator to maintain battery charge level. BLENDED - Both battery and engine are used simultaneously, typically during high power demands. The mode transition typically occurs automatically based on battery state of charge thresholds.
   * Allowed values: ['CHARGE_DEPLETING', 'CHARGE_SUSTAINING', 'BLENDED']
   */
  attribute def Vehicle_Powertrain_RangeExtender_OperatingMode : String;

  /* VSS path: Vehicle.Powertrain.TimeRemaining
   * VSS kind: sensor
   * VSS datatype: uint32
   * Standard quantity reference: ISQ::time
   * Standard unit reference: SI::second
   * Description: Time remaining in seconds before all energy sources available in the vehicle are empty.
   */
  attribute def Vehicle_Powertrain_TimeRemaining : Integer;

  /* VSS path: Vehicle.Powertrain.TractionBattery.AccumulatedChargedEnergy
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::energy
   * Standard unit reference: SI::kilowattHour
   * Description: The accumulated energy delivered to the battery during charging over lifetime of the battery.
   */
  attribute def Vehicle_Powertrain_TractionBattery_AccumulatedChargedEnergy : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.AccumulatedChargedThroughput
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::electricCharge
   * Standard unit reference: SI::ampereHour
   * Description: The accumulated charge throughput delivered to the battery during charging over lifetime of the battery.
   */
  attribute def Vehicle_Powertrain_TractionBattery_AccumulatedChargedThroughput : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.AccumulatedConsumedEnergy
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::energy
   * Standard unit reference: SI::kilowattHour
   * Description: The accumulated energy leaving HV battery for propulsion and auxiliary loads over lifetime of the battery.
   */
  attribute def Vehicle_Powertrain_TractionBattery_AccumulatedConsumedEnergy : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.AccumulatedConsumedThroughput
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::electricCharge
   * Standard unit reference: SI::ampereHour
   * Description: The accumulated charge throughput leaving HV battery for propulsion and auxiliary loads over lifetime of the battery.
   */
  attribute def Vehicle_Powertrain_TractionBattery_AccumulatedConsumedThroughput : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.BatteryConditioning.IsActive
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if battery conditioning is active (i.e. actively monitors battery temperature). True = Active. False = Inactive.
   * Comment: This signal is typically true when mode is not INACTIVE and time is within defined start/end times.
   */
  attribute def Vehicle_Powertrain_TractionBattery_BatteryConditioning_IsActive : Boolean;

  /* VSS path: Vehicle.Powertrain.TractionBattery.BatteryConditioning.IsOngoing
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicating if battery conditioning is currently ongoing. Battery conditioning is considered ongoing when the battery conditioning system is actively heating or cooling the battery, or requesting heating or cooling.
   * Comment: When battery conditioning is active, but temperature is already within acceptable range so that no cooling or heating is needed then IsOngoing shall report False.
   */
  attribute def Vehicle_Powertrain_TractionBattery_BatteryConditioning_IsOngoing : Boolean;

  /* VSS path: Vehicle.Powertrain.TractionBattery.BatteryConditioning.RequestedMode
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Defines requested mode for battery conditioning. INACTIVE - Battery conditioning inactive. FAST_CHARGING_PREPARATION - Battery conditioning for fast charging. DRIVING_PREPARATION - Battery conditioning for driving.
   * Comment: The Mode and TargetTime can be used to calculate TargetTemperature and StartTime
   * Allowed values: ['INACTIVE', 'FAST_CHARGING_PREPARATION', 'DRIVING_PREPARATION']
   */
  attribute def Vehicle_Powertrain_TractionBattery_BatteryConditioning_RequestedMode : String;

  /* VSS path: Vehicle.Powertrain.TractionBattery.BatteryConditioning.StartTime
   * VSS kind: actuator
   * VSS datatype: string
   * Standard quantity reference: n/a
   * Standard unit reference: ISO 8601 lexical date/time string
   * Description: Start time for battery conditioning, formatted according to ISO 8601 with UTC time zone.
   * Comment: If the vehicle is asleep, this is the time the vehicle and the battery conditioning system must wake up and start monitoring the battery and if necessary start heating/cooling of the battery.
   */
  attribute def Vehicle_Powertrain_TractionBattery_BatteryConditioning_StartTime : String;

  /* VSS path: Vehicle.Powertrain.TractionBattery.BatteryConditioning.TargetTemperature
   * VSS kind: actuator
   * VSS datatype: float
   * Standard quantity reference: ISQ::thermodynamicTemperature
   * Standard unit reference: SI::degreeCelsius
   * Description: Target temperature for battery conditioning.
   * Comment: Target temperature possibly differs between different modes as well as other factors. Allowed deviation from target temperature is implementation dependent.
   */
  attribute def Vehicle_Powertrain_TractionBattery_BatteryConditioning_TargetTemperature : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.BatteryConditioning.TargetTime
   * VSS kind: actuator
   * VSS datatype: string
   * Standard quantity reference: n/a
   * Standard unit reference: ISO 8601 lexical date/time string
   * Description: Target time when conditioning shall be finished, formatted according to ISO 8601 with UTC time zone.
   * Comment: For FAST_CHARGING mode this is typically the time when charging is supposed to start. For DRIVING mode this is typically the expected departure time. Battery conditioning will be deactivated when this time has passed.
   */
  attribute def Vehicle_Powertrain_TractionBattery_BatteryConditioning_TargetTime : String;

  /* VSS path: Vehicle.Powertrain.TractionBattery.CellVoltage.CellVoltages
   * VSS kind: sensor
   * VSS datatype: float[]
   * Description: Array of cell voltages. Length or array shall correspond to number of cells in vehicle.
   * Comment: Cells are identified by relative position in array.
   */
  attribute def Vehicle_Powertrain_TractionBattery_CellVoltage_CellVoltages : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.CellVoltage.IdMax
   * VSS kind: sensor
   * VSS datatype: uint16
   * Description: Identifier of the battery cell with highest voltage.
   * Comment: Identifier is supposed to be relative index of the cell, starting with 0 the first cell.
   */
  attribute def Vehicle_Powertrain_TractionBattery_CellVoltage_IdMax : Integer;

  /* VSS path: Vehicle.Powertrain.TractionBattery.CellVoltage.IdMin
   * VSS kind: sensor
   * VSS datatype: uint16
   * Description: Identifier of the battery cell with lowest voltage.
   * Comment: Identifier is supposed to be relative index of the cell, starting with 0 the first cell.
   */
  attribute def Vehicle_Powertrain_TractionBattery_CellVoltage_IdMin : Integer;

  /* VSS path: Vehicle.Powertrain.TractionBattery.CellVoltage.Max
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::electricPotential
   * Standard unit reference: SI::volt
   * Description: Current voltage of the battery cell with highest voltage.
   */
  attribute def Vehicle_Powertrain_TractionBattery_CellVoltage_Max : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.CellVoltage.Min
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::electricPotential
   * Standard unit reference: SI::volt
   * Description: Current voltage of the battery cell with lowest voltage.
   */
  attribute def Vehicle_Powertrain_TractionBattery_CellVoltage_Min : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.AveragePower
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::power
   * Standard unit reference: SI::kilowatt
   * Description: Average charging power of last or current charging event.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_AveragePower : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.ChargeCurrent.DC
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::electricCurrent
   * Standard unit reference: SI::ampere
   * Description: Current DC charging current at inlet. Negative if returning energy to grid.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargeCurrent_DC : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.ChargeCurrent.Phase1
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::electricCurrent
   * Standard unit reference: SI::ampere
   * Description: Current AC charging current (rms) at inlet for Phase 1. Negative if returning energy to grid.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargeCurrent_Phase1 : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.ChargeCurrent.Phase2
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::electricCurrent
   * Standard unit reference: SI::ampere
   * Description: Current AC charging current (rms) at inlet for Phase 2. Negative if returning energy to grid.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargeCurrent_Phase2 : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.ChargeCurrent.Phase3
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::electricCurrent
   * Standard unit reference: SI::ampere
   * Description: Current AC charging current (rms) at inlet for Phase 3. Negative if returning energy to grid.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargeCurrent_Phase3 : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.ChargeLimit
   * VSS kind: actuator
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Target charge limit (state of charge) for battery.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargeLimit : Integer;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.ChargeRate
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::speed
   * Standard unit reference: SI::kilometrePerHour
   * Description: Current charging rate, as in kilometers of range added per hour.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargeRate : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.ChargeVoltage.DC
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::electricPotential
   * Standard unit reference: SI::volt
   * Description: Current DC charging voltage at charging inlet.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargeVoltage_DC : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.ChargeVoltage.Phase1
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::electricPotential
   * Standard unit reference: SI::volt
   * Description: Current AC charging voltage (rms) at inlet for Phase 1.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargeVoltage_Phase1 : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.ChargeVoltage.Phase2
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::electricPotential
   * Standard unit reference: SI::volt
   * Description: Current AC charging voltage (rms) at inlet for Phase 2.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargeVoltage_Phase2 : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.ChargeVoltage.Phase3
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::electricPotential
   * Standard unit reference: SI::volt
   * Description: Current AC charging voltage (rms) at inlet for Phase 3.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargeVoltage_Phase3 : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.ChargingPort.IsChargingCableConnected
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates whether a charging cable is physically connected to a particular charging port or not.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargingPort_IsChargingCableConnected : Boolean;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.ChargingPort.IsChargingCableLocked
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is charging cable locked to prevent removal.
   * Comment: Locking of charging cable can be used to prevent unintentional removing during charging.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargingPort_IsChargingCableLocked : Boolean;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.ChargingPort.IsFlapOpen
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Status of the charging port flap(s).
   * Comment: True = at least one flap of this port is open, False = All flaps of this port are closed.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargingPort_IsFlapOpen : Boolean;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.ChargingPort.SupportedInletTypes
   * VSS kind: attribute
   * VSS datatype: string[]
   * Description: A list of the supported (i.e., available) charging inlets in a particular charging port. IEC types refer to IEC 62196, GBT refers to GB/T 20234.
   * Comment: A vehicle may have multiple charging ports. IEC_TYPE_1_AC refers to Type 1 as defined in IEC 62196-2. Also known as Yazaki or J1772 connector. IEC_TYPE_2_AC refers to Type 2 as defined in IEC 62196-2. Also known as Mennekes connector. IEC_TYPE_3_AC refers to Type 3 as defined in IEC 62196-2. Also known as Scame connector. IEC_TYPE_4_DC refers to AA configuration as defined in IEC 62196-3. Also known as Type 4 or CHAdeMO connector. IEC_TYPE_1_CCS_DC refers to EE Configuration as defined in IEC 62196-3. Also known as CCS1 or Combo1 connector. IEC_TYPE_2_CCS_DC refers to FF Configuration as defined in IEC 62196-3. Also known as CCS2 or Combo2 connector. TESLA_ROADSTER, TESLA_HPWC (High Power Wall Connector) and TESLA_SUPERCHARGER refer to non-standardized charging ports/methods used by Tesla. GBT_AC refers to connector specified in GB/T 20234.2. GBT_DC refers to connector specified in GB/T 20234.3. Also specified as BB Configuration in IEC 62196-3. OTHER shall be used for charging ports not included in the list above. For additional information see https://en.wikipedia.org/wiki/IEC_62196.
   * Allowed values: ['IEC_TYPE_1_AC', 'IEC_TYPE_2_AC', 'IEC_TYPE_3_AC', 'IEC_TYPE_4_DC', 'IEC_TYPE_1_CCS_DC', 'IEC_TYPE_2_CCS_DC', 'TESLA_ROADSTER', 'TESLA_HPWC', 'TESLA_SUPERCHARGER', 'GBT_AC', 'GBT_DC', 'OTHER']
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargingPort_SupportedInletTypes : String;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.EvseId
   * VSS kind: sensor
   * VSS datatype: string
   * Description: EVSE charging point ID (without separators) of last or current charging event according to ISO 15118-2 Annex H.
   * Comment: Length of id between 7 and 37 characters. ZZ00000 to be used if SECC cannot provide id
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_EvseId : String;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.IsCharging
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: True if charging is ongoing. Charging is considered to be ongoing if energy is flowing from charger to vehicle.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_IsCharging : Boolean;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.IsDischarging
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: True if discharging (vehicle to grid) is ongoing. Discharging is considered to be ongoing if energy is flowing from vehicle to charger/grid.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_IsDischarging : Boolean;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.Location.Altitude
   * VSS kind: sensor
   * VSS datatype: double
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::metre
   * Description: Altitude relative to WGS 84 reference ellipsoid of last or current charging event.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_Location_Altitude : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.Location.Latitude
   * VSS kind: sensor
   * VSS datatype: double
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Latitude of last or current charging event in WGS 84 geodetic coordinates.
   * Value range: min=-90, max=90
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_Location_Latitude : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.Location.Longitude
   * VSS kind: sensor
   * VSS datatype: double
   * Standard quantity reference: ISQ::planeAngle
   * Standard unit reference: SI::degree
   * Description: Longitude of last or current charging event in WGS 84 geodetic coordinates.
   * Value range: min=-180, max=180
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_Location_Longitude : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.MaxPower
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::power
   * Standard unit reference: SI::kilowatt
   * Description: Maximum charging power of last or current charging event.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_MaxPower : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.MaximumChargingCurrent.DC
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::electricCurrent
   * Standard unit reference: SI::ampere
   * Description: Maximum DC charging current at inlet that can be accepted by the system.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_MaximumChargingCurrent_DC : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.MaximumChargingCurrent.Phase1
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::electricCurrent
   * Standard unit reference: SI::ampere
   * Description: Maximum AC charging current (rms) at inlet for Phase 1 that can be accepted by the system.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_MaximumChargingCurrent_Phase1 : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.MaximumChargingCurrent.Phase2
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::electricCurrent
   * Standard unit reference: SI::ampere
   * Description: Maximum AC charging current (rms) at inlet for Phase 2 that can be accepted by the system.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_MaximumChargingCurrent_Phase2 : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.MaximumChargingCurrent.Phase3
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::electricCurrent
   * Standard unit reference: SI::ampere
   * Description: Maximum AC charging current (rms) at inlet for Phase 3 that can be accepted by the system.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_MaximumChargingCurrent_Phase3 : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.PowerLoss
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::power
   * Standard unit reference: SI::watt
   * Description: Electrical energy lost by power dissipation to heat inside the AC/DC converter.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_PowerLoss : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.StartStopCharging
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Start or stop the charging process.
   * Allowed values: ['START', 'STOP']
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_StartStopCharging : String;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.Temperature
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::thermodynamicTemperature
   * Standard unit reference: SI::degreeCelsius
   * Description: Current temperature of AC/DC converter converting grid voltage to battery voltage.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_Temperature : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.TimeToComplete
   * VSS kind: sensor
   * VSS datatype: uint32
   * Standard quantity reference: ISQ::time
   * Standard unit reference: SI::second
   * Description: The time needed for the current charging process to reach Charging.ChargeLimit. 0 if charging is complete or no charging process is active or planned.
   * Comment: Shall consider time set by Charging.Timer.Time. E.g. if charging shall start in 3 hours and 2 hours of charging is needed, then Charging.TimeToComplete shall report 5 hours.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_TimeToComplete : Integer;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.Timer.Mode
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Defines timer mode for charging: INACTIVE - no timer set, charging may start as soon as battery is connected to a charger. START_TIME - charging shall start at Charging.Timer.Time. END_TIME - charging shall be finished (reach Charging.ChargeLimit) at Charging.Timer.Time. When charging is completed the vehicle shall change mode to 'inactive' or set a new Charging.Timer.Time. Charging shall start immediately if mode is 'starttime' or 'endtime' and Charging.Timer.Time is a time in the past.
   * Allowed values: ['INACTIVE', 'START_TIME', 'END_TIME']
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_Timer_Mode : String;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Charging.Timer.Time
   * VSS kind: actuator
   * VSS datatype: string
   * Standard quantity reference: n/a
   * Standard unit reference: ISO 8601 lexical date/time string
   * Description: Time for next charging-related action, formatted according to ISO 8601 with UTC time zone. Value has no significance if Charging.Timer.Mode is 'inactive'.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Charging_Timer_Time : String;

  /* VSS path: Vehicle.Powertrain.TractionBattery.CurrentCurrent
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::electricCurrent
   * Standard unit reference: SI::ampere
   * Description: Current current flowing in/out of battery. Positive = Current flowing in to battery, e.g. during charging. Negative = Current flowing out of battery, e.g. during driving.
   */
  attribute def Vehicle_Powertrain_TractionBattery_CurrentCurrent : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.CurrentPower
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::power
   * Standard unit reference: SI::watt
   * Description: Current electrical energy flowing in/out of battery. Positive = Energy flowing in to battery, e.g. during charging. Negative = Energy flowing out of battery, e.g. during driving.
   */
  attribute def Vehicle_Powertrain_TractionBattery_CurrentPower : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.CurrentVoltage
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::electricPotential
   * Standard unit reference: SI::volt
   * Description: Current Voltage of the battery.
   */
  attribute def Vehicle_Powertrain_TractionBattery_CurrentVoltage : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.DCDC.PowerLoss
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::power
   * Standard unit reference: SI::watt
   * Description: Electrical energy lost by power dissipation to heat inside DC/DC converter.
   */
  attribute def Vehicle_Powertrain_TractionBattery_DCDC_PowerLoss : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.DCDC.Temperature
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::thermodynamicTemperature
   * Standard unit reference: SI::degreeCelsius
   * Description: Current temperature of DC/DC converter converting battery high voltage to vehicle low voltage (typically 12 Volts).
   */
  attribute def Vehicle_Powertrain_TractionBattery_DCDC_Temperature : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.ErrorCodes
   * VSS kind: sensor
   * VSS datatype: string[]
   * Description: Current error codes related to the battery, if any.
   * Comment: Error code format is not defined, it may be DTCs according to OBD II (SAE-J2012DA_201812) standard ([P|C|B|U]XXXXX ) or any other format.
   */
  attribute def Vehicle_Powertrain_TractionBattery_ErrorCodes : String;

  /* VSS path: Vehicle.Powertrain.TractionBattery.GrossCapacity
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::energy
   * Standard unit reference: SI::kilowattHour
   * Description: Gross capacity of the battery.
   */
  attribute def Vehicle_Powertrain_TractionBattery_GrossCapacity : Integer;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Id
   * VSS kind: attribute
   * VSS datatype: string
   * Description: Battery Identification Number as assigned by OEM.
   * Comment: This could be serial number, part number plus serial number, UUID, or any other identifier that the OEM want to use to uniquely identify the battery individual.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Id : String;

  /* VSS path: Vehicle.Powertrain.TractionBattery.IsGroundConnected
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicating if the ground (negative terminator) of the traction battery is connected to the powertrain.
   * Comment: It might be possible to disconnect the traction battery used by an electric powertrain. This is achieved by connectors, typically one for plus and one for minus.
   */
  attribute def Vehicle_Powertrain_TractionBattery_IsGroundConnected : Boolean;

  /* VSS path: Vehicle.Powertrain.TractionBattery.IsPowerConnected
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicating if the power (positive terminator) of the traction battery is connected to the powertrain.
   * Comment: It might be possible to disconnect the traction battery used by an electric powertrain. This is achieved by connectors, typically one for plus and one for minus.
   */
  attribute def Vehicle_Powertrain_TractionBattery_IsPowerConnected : Boolean;

  /* VSS path: Vehicle.Powertrain.TractionBattery.MaxVoltage
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::electricPotential
   * Standard unit reference: SI::volt
   * Description: Max allowed voltage of the battery, e.g. during charging.
   */
  attribute def Vehicle_Powertrain_TractionBattery_MaxVoltage : Integer;

  /* VSS path: Vehicle.Powertrain.TractionBattery.NetCapacity
   * VSS kind: sensor
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::energy
   * Standard unit reference: SI::kilowattHour
   * Description: Total net capacity of the battery considering aging.
   */
  attribute def Vehicle_Powertrain_TractionBattery_NetCapacity : Integer;

  /* VSS path: Vehicle.Powertrain.TractionBattery.NominalVoltage
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::electricPotential
   * Standard unit reference: SI::volt
   * Description: Nominal Voltage of the battery.
   * Comment: Nominal voltage typically refers to voltage of fully charged battery when delivering rated capacity.
   */
  attribute def Vehicle_Powertrain_TractionBattery_NominalVoltage : Integer;

  /* VSS path: Vehicle.Powertrain.TractionBattery.PowerLoss
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::power
   * Standard unit reference: SI::watt
   * Description: Electrical energy lost by power dissipation to heat inside the battery.
   */
  attribute def Vehicle_Powertrain_TractionBattery_PowerLoss : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.ProductionDate
   * VSS kind: attribute
   * VSS datatype: string
   * Standard quantity reference: n/a
   * Standard unit reference: ISO 8601 lexical date/time string
   * Description: Production date of battery in ISO8601 format, e.g. YYYY-MM-DD.
   */
  attribute def Vehicle_Powertrain_TractionBattery_ProductionDate : String;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Range
   * VSS kind: sensor
   * VSS datatype: uint32
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::metre
   * Description: Remaining range in meters using only battery.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Range : Integer;

  /* VSS path: Vehicle.Powertrain.TractionBattery.StateOfCharge.Current
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Physical state of charge of the high voltage battery, relative to net capacity. This is not necessarily the state of charge being displayed to the customer.
   * Value range: min=0, max=100.0
   */
  attribute def Vehicle_Powertrain_TractionBattery_StateOfCharge_Current : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.StateOfCharge.CurrentEnergy
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::energy
   * Standard unit reference: SI::kilowattHour
   * Description: Physical state of charge of high voltage battery expressed in kWh.
   * Comment: Current energy could be calculated as .StateOfCharge.Current * .NetCapacity.
   */
  attribute def Vehicle_Powertrain_TractionBattery_StateOfCharge_CurrentEnergy : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.StateOfCharge.Displayed
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: State of charge displayed to the customer.
   * Value range: min=0, max=100.0
   */
  attribute def Vehicle_Powertrain_TractionBattery_StateOfCharge_Displayed : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.StateOfHealth
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Calculated battery state of health at standard conditions.
   * Comment: Exact formula is implementation dependent. Could be e.g. current capacity at 20 degrees Celsius divided with original capacity at the same temperature.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Powertrain_TractionBattery_StateOfHealth : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Temperature.Average
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::thermodynamicTemperature
   * Standard unit reference: SI::degreeCelsius
   * Description: Current average temperature of the battery cells.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Temperature_Average : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Temperature.CellTemperature
   * VSS kind: sensor
   * VSS datatype: float[]
   * Description: Array of cell temperatures. Length or array shall correspond to number of cells in vehicle.
   * Comment: Cells are identified by relative position in array.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Temperature_CellTemperature : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Temperature.Max
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::thermodynamicTemperature
   * Standard unit reference: SI::degreeCelsius
   * Description: Current maximum temperature of the battery cells, i.e. temperature of the hottest cell.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Temperature_Max : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.Temperature.Min
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::thermodynamicTemperature
   * Standard unit reference: SI::degreeCelsius
   * Description: Current minimum temperature of the battery cells, i.e. temperature of the coldest cell.
   */
  attribute def Vehicle_Powertrain_TractionBattery_Temperature_Min : Real;

  /* VSS path: Vehicle.Powertrain.TractionBattery.TimeRemaining
   * VSS kind: sensor
   * VSS datatype: uint32
   * Standard quantity reference: ISQ::time
   * Standard unit reference: SI::second
   * Description: Time remaining in seconds before the battery is empty.
   */
  attribute def Vehicle_Powertrain_TractionBattery_TimeRemaining : Integer;

  /* VSS path: Vehicle.Powertrain.Transmission.ClutchEngagement
   * VSS kind: actuator
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Clutch engagement. 0% = Clutch fully disengaged. 100% = Clutch fully engaged.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Powertrain_Transmission_ClutchEngagement : Real;

  /* VSS path: Vehicle.Powertrain.Transmission.ClutchWear
   * VSS kind: sensor
   * VSS datatype: uint8
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Clutch wear as a percent. 0 = no wear. 100 = worn.
   * Value range: min=, max=100
   */
  attribute def Vehicle_Powertrain_Transmission_ClutchWear : Integer;

  /* VSS path: Vehicle.Powertrain.Transmission.CurrentGear
   * VSS kind: sensor
   * VSS datatype: int8
   * Description: The current gear. 0=Neutral, 1/2/..=Forward, -1/-2/..=Reverse.
   */
  attribute def Vehicle_Powertrain_Transmission_CurrentGear : Integer;

  /* VSS path: Vehicle.Powertrain.Transmission.DiffLockFrontEngagement
   * VSS kind: actuator
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Front Diff Lock engagement. 0% = Diff lock fully disengaged. 100% = Diff lock fully engaged.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Powertrain_Transmission_DiffLockFrontEngagement : Real;

  /* VSS path: Vehicle.Powertrain.Transmission.DiffLockRearEngagement
   * VSS kind: actuator
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Rear Diff Lock engagement. 0% = Diff lock fully disengaged. 100% = Diff lock fully engaged.
   * Value range: min=0, max=100
   */
  attribute def Vehicle_Powertrain_Transmission_DiffLockRearEngagement : Real;

  /* VSS path: Vehicle.Powertrain.Transmission.DriveType
   * VSS kind: attribute
   * VSS datatype: string
   * Description: Drive type.
   * Allowed values: ['UNKNOWN', 'FORWARD_WHEEL_DRIVE', 'REAR_WHEEL_DRIVE', 'ALL_WHEEL_DRIVE']
   */
  attribute def Vehicle_Powertrain_Transmission_DriveType : String;

  /* VSS path: Vehicle.Powertrain.Transmission.GearChangeMode
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Is the gearbox in automatic or manual (paddle) mode.
   * Allowed values: ['MANUAL', 'AUTOMATIC']
   */
  attribute def Vehicle_Powertrain_Transmission_GearChangeMode : String;

  /* VSS path: Vehicle.Powertrain.Transmission.GearCount
   * VSS kind: attribute
   * VSS datatype: int8
   * Description: Number of forward gears in the transmission. -1 = CVT.
   */
  attribute def Vehicle_Powertrain_Transmission_GearCount : Integer;

  /* VSS path: Vehicle.Powertrain.Transmission.IsElectricalPowertrainEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is electrical powertrain mechanically connected/engaged to the drivetrain or not. False = Disconnected/Disengaged. True = Connected/Engaged.
   * Comment: In some hybrid solutions it is possible to disconnect/disengage the electrical powertrain mechanically to avoid induced voltage reaching a too high level when driving at high speed.
   */
  attribute def Vehicle_Powertrain_Transmission_IsElectricalPowertrainEngaged : Boolean;

  /* VSS path: Vehicle.Powertrain.Transmission.IsLowRangeEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is gearbox in low range mode or not. False = Normal/High range engaged. True = Low range engaged.
   * Comment: The possibility to switch between low and high gear range is typically only available in heavy vehicles and off-road vehicles.
   */
  attribute def Vehicle_Powertrain_Transmission_IsLowRangeEngaged : Boolean;

  /* VSS path: Vehicle.Powertrain.Transmission.IsParkLockEngaged
   * VSS kind: actuator
   * VSS datatype: boolean
   * Description: Is the transmission park lock engaged or not. False = Disengaged. True = Engaged.
   */
  attribute def Vehicle_Powertrain_Transmission_IsParkLockEngaged : Boolean;

  /* VSS path: Vehicle.Powertrain.Transmission.PerformanceMode
   * VSS kind: actuator
   * VSS datatype: string
   * Description: Current gearbox performance mode.
   * Allowed values: ['NORMAL', 'SPORT', 'ECONOMY', 'SNOW', 'RAIN']
   */
  attribute def Vehicle_Powertrain_Transmission_PerformanceMode : String;

  /* VSS path: Vehicle.Powertrain.Transmission.SelectedGear
   * VSS kind: actuator
   * VSS datatype: int8
   * Description: The selected gear. 0=Neutral, 1/2/..=Forward, -1/-2/..=Reverse, 126=Park, 127=Drive.
   */
  attribute def Vehicle_Powertrain_Transmission_SelectedGear : Integer;

  /* VSS path: Vehicle.Powertrain.Transmission.Temperature
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::thermodynamicTemperature
   * Standard unit reference: SI::degreeCelsius
   * Description: The current gearbox temperature.
   */
  attribute def Vehicle_Powertrain_Transmission_Temperature : Real;

  /* VSS path: Vehicle.Powertrain.Transmission.TorqueDistribution
   * VSS kind: actuator
   * VSS datatype: float
   * Standard quantity reference: ISQ::dimensionless
   * Standard unit reference: SI::percent
   * Description: Torque distribution between front and rear axle in percent. -100% = Full torque to front axle, 0% = 50:50 Front/Rear, 100% = Full torque to rear axle.
   * Value range: min=-100, max=100
   */
  attribute def Vehicle_Powertrain_Transmission_TorqueDistribution : Real;

  /* VSS path: Vehicle.Powertrain.Transmission.TravelledDistance
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::kilometre
   * Description: Odometer reading, total distance travelled during the lifetime of the transmission.
   */
  attribute def Vehicle_Powertrain_Transmission_TravelledDistance : Real;

  /* VSS path: Vehicle.Powertrain.Transmission.Type
   * VSS kind: attribute
   * VSS datatype: string
   * Description: Transmission type.
   * Allowed values: ['UNKNOWN', 'SEQUENTIAL', 'H', 'AUTOMATIC', 'DSG', 'CVT']
   */
  attribute def Vehicle_Powertrain_Transmission_Type : String;

  /* VSS path: Vehicle.Powertrain.Type
   * VSS kind: attribute
   * VSS datatype: string
   * Description: Defines the powertrain type of the vehicle.
   * Comment: For vehicles with a combustion engine (including hybrids) more detailed information on fuels supported can be found in FuelSystem.SupportedFuelTypes and FuelSystem.SupportedFuels.
   * Allowed values: ['COMBUSTION', 'HYBRID', 'ELECTRIC']
   */
  attribute def Vehicle_Powertrain_Type : String;

  /* VSS path: Vehicle.RoofLoad
   * VSS kind: attribute
   * VSS datatype: int16
   * Standard quantity reference: ISQ::mass
   * Standard unit reference: SI::kilogram
   * Description: The permitted total weight of cargo and installations (e.g. a roof rack) on top of the vehicle.
   */
  attribute def Vehicle_RoofLoad : Integer;

  /* VSS path: Vehicle.Safety.IsFire
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates whether a fire has been detected in or on the vehicle.
   * Comment: Determination method is implementation specific. May be derived from temperature sensors, battery thermal runaway detection, or dedicated fire/smoke detection systems. Primary consumers: emergency dispatch and first responder systems. Related to VSS issue #877 (Connected Safety signals).
   */
  attribute def Vehicle_Safety_IsFire : Boolean;

  /* VSS path: Vehicle.Safety.IsSubmersed
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates whether the vehicle is partially or fully submersed in water.
   * Comment: Determination method is implementation specific. May be derived from pressure sensors, water contact sensors, door seal sensors, or anomalous rain detection intensity readings. Primary consumers: emergency dispatch and first responder systems. Related to VSS issue #877 (Connected Safety signals).
   */
  attribute def Vehicle_Safety_IsSubmersed : Boolean;

  /* VSS path: Vehicle.Safety.Rollover
   * VSS kind: sensor
   * VSS datatype: string
   * Description: Indicates whether the vehicle has rolled over or is at risk of rollover.
   * Comment: May be derived from Vehicle.AngularVelocity, Vehicle.Orientation.Roll, and Vehicle.Orientation.Pitch signals. NONE indicates normal orientation. RISK indicates the vehicle is at elevated risk of rollover. DETECTED indicates a rollover event has occurred. UNKNOWN shall be used when the system cannot assess rollover status. Criteria for each state may be OEM specific. Primary consumers: emergency dispatch and first responder systems. Related to VSS issue #877 (Connected Safety signals).
   * Allowed values: ['UNKNOWN', 'NONE', 'RISK', 'DETECTED']
   */
  attribute def Vehicle_Safety_Rollover : String;

  /* VSS path: Vehicle.Service.DistanceToService
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::kilometre
   * Description: Remaining distance to service (of any kind). Negative values indicate service overdue.
   */
  attribute def Vehicle_Service_DistanceToService : Real;

  /* VSS path: Vehicle.Service.IsServiceDue
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Indicates if vehicle needs service (of any kind). True = Service needed now or in the near future. False = No known need for service.
   */
  attribute def Vehicle_Service_IsServiceDue : Boolean;

  /* VSS path: Vehicle.Service.TimeToService
   * VSS kind: sensor
   * VSS datatype: int32
   * Standard quantity reference: ISQ::time
   * Standard unit reference: SI::second
   * Description: Remaining time to service (of any kind). Negative values indicate service overdue.
   */
  attribute def Vehicle_Service_TimeToService : Integer;

  /* VSS path: Vehicle.Speed
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::speed
   * Standard unit reference: SI::kilometrePerHour
   * Description: Vehicle speed.
   */
  attribute def Vehicle_Speed : Real;

  /* VSS path: Vehicle.StartTime
   * VSS kind: attribute
   * VSS datatype: string
   * Standard quantity reference: n/a
   * Standard unit reference: ISO 8601 lexical date/time string
   * Description: Start time of current or latest trip, formatted according to ISO 8601 with UTC time zone.
   * Comment: This signal is supposed to be set whenever a new trip starts. A new trip is considered to start when engine gets enabled (e.g. LowVoltageSystemState in ON or START mode). A trip is considered to end when engine is no longer enabled. The default value indicates that the vehicle never has been started, or that latest start time is unknown.
   */
  attribute def Vehicle_StartTime : String;

  /* VSS path: Vehicle.Trailer.IsConnected
   * VSS kind: sensor
   * VSS datatype: boolean
   * Description: Signal indicating if trailer is connected or not.
   */
  attribute def Vehicle_Trailer_IsConnected : Boolean;

  /* VSS path: Vehicle.TraveledDistance
   * VSS kind: sensor
   * VSS datatype: uint32
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::metre
   * Description: Odometer reading, total distance traveled during the lifetime of the vehicle.
   */
  attribute def Vehicle_TraveledDistance : Integer;

  /* VSS path: Vehicle.TraveledDistanceSinceStart
   * VSS kind: sensor
   * VSS datatype: uint32
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::metre
   * Description: Distance traveled since start of current trip.
   * Comment: A new trip is considered to start when engine gets enabled (e.g. LowVoltageSystemState in ON or START mode). A trip is considered to end when engine is no longer enabled. The signal may however keep the value of the last trip until a new trip is started.
   */
  attribute def Vehicle_TraveledDistanceSinceStart : Integer;

  /* VSS path: Vehicle.TripDuration
   * VSS kind: sensor
   * VSS datatype: float
   * Standard quantity reference: ISQ::time
   * Standard unit reference: SI::second
   * Description: Duration of latest trip.
   * Comment: This signal is not assumed to be continuously updated, but instead set to 0 when a trip starts and set to the actual duration of the trip when a trip ends. A new trip is considered to start when engine gets enabled (e.g. LowVoltageSystemState in ON or START mode). A trip is considered to end when engine is no longer enabled.
   */
  attribute def Vehicle_TripDuration : Real;

  /* VSS path: Vehicle.TripMeterReading
   * VSS kind: actuator
   * VSS datatype: uint32
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::metre
   * Description: Trip meter reading.
   * Comment: The trip meter is an odometer that can be manually reset by the driver
   */
  attribute def Vehicle_TripMeterReading : Integer;

  /* VSS path: Vehicle.TurningDiameter
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: Minimum turning diameter, Wall-to-Wall, as defined by SAE J1100-2009 D102.
   */
  attribute def Vehicle_TurningDiameter : Integer;

  /* VSS path: Vehicle.VehicleIdentification.AcrissCode
   * VSS kind: attribute
   * VSS datatype: string
   * Description: The ACRISS Car Classification Code is a code used by many car rental companies.
   */
  attribute def Vehicle_VehicleIdentification_AcrissCode : String;

  /* VSS path: Vehicle.VehicleIdentification.BodyType
   * VSS kind: attribute
   * VSS datatype: string
   * Description: Indicates the design and body style of the vehicle (e.g. station wagon, hatchback, etc.).
   */
  attribute def Vehicle_VehicleIdentification_BodyType : String;

  /* VSS path: Vehicle.VehicleIdentification.Brand
   * VSS kind: attribute
   * VSS datatype: string
   * Description: Vehicle brand or manufacturer.
   */
  attribute def Vehicle_VehicleIdentification_Brand : String;

  /* VSS path: Vehicle.VehicleIdentification.DateVehicleFirstRegistered
   * VSS kind: attribute
   * VSS datatype: string
   * Standard quantity reference: n/a
   * Standard unit reference: ISO 8601 lexical date/time string
   * Description: The date in ISO 8601 format of the first registration of the vehicle with the respective public authorities.
   */
  attribute def Vehicle_VehicleIdentification_DateVehicleFirstRegistered : String;

  /* VSS path: Vehicle.VehicleIdentification.KnownVehicleDamages
   * VSS kind: attribute
   * VSS datatype: string
   * Description: A textual description of known damages, both repaired and unrepaired.
   */
  attribute def Vehicle_VehicleIdentification_KnownVehicleDamages : String;

  /* VSS path: Vehicle.VehicleIdentification.LicensePlate
   * VSS kind: attribute
   * VSS datatype: string
   * Description: The license plate of the vehicle.
   * Comment: Depending on the context, this attribute might not be up to date or might be misconfigured, and therefore should be considered untrustworthy in the absence of another method of verification.
   */
  attribute def Vehicle_VehicleIdentification_LicensePlate : String;

  /* VSS path: Vehicle.VehicleIdentification.MeetsEmissionStandard
   * VSS kind: attribute
   * VSS datatype: string
   * Description: Indicates that the vehicle meets the respective emission standard.
   */
  attribute def Vehicle_VehicleIdentification_MeetsEmissionStandard : String;

  /* VSS path: Vehicle.VehicleIdentification.Model
   * VSS kind: attribute
   * VSS datatype: string
   * Description: Vehicle model.
   */
  attribute def Vehicle_VehicleIdentification_Model : String;

  /* VSS path: Vehicle.VehicleIdentification.OptionalExtras
   * VSS kind: attribute
   * VSS datatype: string[]
   * Description: Optional extras refers to all car equipment options that are not installed as standard by the manufacturer.
   * Comment: Allowed values are not standardized, each OEM can specify detail descriptions of array elements.
   */
  attribute def Vehicle_VehicleIdentification_OptionalExtras : String;

  /* VSS path: Vehicle.VehicleIdentification.ProductionDate
   * VSS kind: attribute
   * VSS datatype: string
   * Standard quantity reference: n/a
   * Standard unit reference: ISO 8601 lexical date/time string
   * Description: The date in ISO 8601 format of production of the item, e.g. vehicle.
   */
  attribute def Vehicle_VehicleIdentification_ProductionDate : String;

  /* VSS path: Vehicle.VehicleIdentification.PurchaseDate
   * VSS kind: attribute
   * VSS datatype: string
   * Standard quantity reference: n/a
   * Standard unit reference: ISO 8601 lexical date/time string
   * Description: The date in ISO 8601 format of the item e.g. vehicle was purchased by the current owner.
   */
  attribute def Vehicle_VehicleIdentification_PurchaseDate : String;

  /* VSS path: Vehicle.VehicleIdentification.VIN
   * VSS kind: attribute
   * VSS datatype: string
   * Description: 17-character Vehicle Identification Number (VIN) as defined by ISO 3779.
   */
  attribute def Vehicle_VehicleIdentification_VIN : String;

  /* VSS path: Vehicle.VehicleIdentification.VehicleConfiguration
   * VSS kind: attribute
   * VSS datatype: string
   * Description: A short text indicating the configuration of the vehicle, e.g. '5dr hatchback ST 2.5 MT 225 hp' or 'limited edition'.
   */
  attribute def Vehicle_VehicleIdentification_VehicleConfiguration : String;

  /* VSS path: Vehicle.VehicleIdentification.VehicleExteriorColor
   * VSS kind: attribute
   * VSS datatype: string
   * Description: The main color of the exterior within the basic color palette (eg. red, blue, black, white, ...).
   */
  attribute def Vehicle_VehicleIdentification_VehicleExteriorColor : String;

  /* VSS path: Vehicle.VehicleIdentification.VehicleInteriorColor
   * VSS kind: attribute
   * VSS datatype: string
   * Description: The color or color combination of the interior of the vehicle.
   */
  attribute def Vehicle_VehicleIdentification_VehicleInteriorColor : String;

  /* VSS path: Vehicle.VehicleIdentification.VehicleInteriorType
   * VSS kind: attribute
   * VSS datatype: string
   * Description: The type or material of the interior of the vehicle (e.g. synthetic fabric, leather, wood, etc.).
   */
  attribute def Vehicle_VehicleIdentification_VehicleInteriorType : String;

  /* VSS path: Vehicle.VehicleIdentification.VehicleModelDate
   * VSS kind: attribute
   * VSS datatype: string
   * Standard quantity reference: n/a
   * Standard unit reference: ISO 8601 lexical date/time string
   * Description: The release date in ISO 8601 format of a vehicle model (often used to differentiate versions of the same make and model).
   */
  attribute def Vehicle_VehicleIdentification_VehicleModelDate : String;

  /* VSS path: Vehicle.VehicleIdentification.VehicleSeatingCapacity
   * VSS kind: attribute
   * VSS datatype: uint16
   * Description: The number of passengers that can be seated in the vehicle, both in terms of the physical space available, and in terms of limitations set by law.
   */
  attribute def Vehicle_VehicleIdentification_VehicleSeatingCapacity : Integer;

  /* VSS path: Vehicle.VehicleIdentification.VehicleSpecialUsage
   * VSS kind: attribute
   * VSS datatype: string
   * Description: Indicates whether the vehicle has been used for special purposes, like commercial rental, driving school.
   */
  attribute def Vehicle_VehicleIdentification_VehicleSpecialUsage : String;

  /* VSS path: Vehicle.VehicleIdentification.WMI
   * VSS kind: attribute
   * VSS datatype: string
   * Description: 3-character World Manufacturer Identification (WMI) as defined by ISO 3780.
   */
  attribute def Vehicle_VehicleIdentification_WMI : String;

  /* VSS path: Vehicle.VehicleIdentification.Year
   * VSS kind: attribute
   * VSS datatype: uint16
   * Description: Model year of the vehicle.
   */
  attribute def Vehicle_VehicleIdentification_Year : Integer;

  /* VSS path: Vehicle.VersionVSS.Label
   * VSS kind: attribute
   * VSS datatype: string
   * Description: Label to further describe the version.
   * Comment: COVESA VSS project typically use dev for latest master, and empty string for released versions.
   */
  attribute def Vehicle_VersionVSS_Label : String;

  /* VSS path: Vehicle.VersionVSS.Major
   * VSS kind: attribute
   * VSS datatype: uint32
   * Description: Supported Version of VSS - Major version.
   */
  attribute def Vehicle_VersionVSS_Major : Integer;

  /* VSS path: Vehicle.VersionVSS.Minor
   * VSS kind: attribute
   * VSS datatype: uint32
   * Description: Supported Version of VSS - Minor version.
   */
  attribute def Vehicle_VersionVSS_Minor : Integer;

  /* VSS path: Vehicle.VersionVSS.Patch
   * VSS kind: attribute
   * VSS datatype: uint32
   * Description: Supported Version of VSS - Patch version.
   */
  attribute def Vehicle_VersionVSS_Patch : Integer;

  /* VSS path: Vehicle.WidthExcludingMirrors
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: Overall vehicle width excluding mirrors, as defined by SAE J1100-2009 W103.
   */
  attribute def Vehicle_WidthExcludingMirrors : Integer;

  /* VSS path: Vehicle.WidthFoldedMirrors
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: Overall vehicle width with mirrors folded, as defined by SAE J1100-2009 W145.
   */
  attribute def Vehicle_WidthFoldedMirrors : Integer;

  /* VSS path: Vehicle.WidthIncludingMirrors
   * VSS kind: attribute
   * VSS datatype: uint16
   * Standard quantity reference: ISQ::length
   * Standard unit reference: SI::millimetre
   * Description: Overall vehicle width including mirrors, as defined by SAE J1100-2009 W144.
   */
  attribute def Vehicle_WidthIncludingMirrors : Integer;

}

package BranchDefinitions {
  /* VSS branch: Vehicle — High-level vehicle data. */
  part def Vehicle;
  /* VSS branch: Vehicle.ADAS — All Advanced Driver Assist Systems data. */
  part def Vehicle_ADAS;
  /* VSS branch: Vehicle.ADAS.ABS — Antilock Braking System signals. */
  part def Vehicle_ADAS_ABS;
  /* VSS branch: Vehicle.ADAS.CruiseControl — Signals from Cruise Control system. */
  part def Vehicle_ADAS_CruiseControl;
  /* VSS branch: Vehicle.ADAS.DMS — Driver Monitoring System signals. */
  part def Vehicle_ADAS_DMS;
  /* VSS branch: Vehicle.ADAS.EBA — Emergency Brake Assist (EBA) System signals. */
  part def Vehicle_ADAS_EBA;
  /* VSS branch: Vehicle.ADAS.EBD — Electronic Brakeforce Distribution (EBD) System signals. */
  part def Vehicle_ADAS_EBD;
  /* VSS branch: Vehicle.ADAS.ESC — Electronic Stability Control System signals. */
  part def Vehicle_ADAS_ESC;
  /* VSS branch: Vehicle.ADAS.ESC.RoadFriction — Road friction values reported by the ESC system. */
  part def Vehicle_ADAS_ESC_RoadFriction;
  /* VSS branch: Vehicle.ADAS.LaneDepartureDetection — Signals from Lane Departure Detection System. */
  part def Vehicle_ADAS_LaneDepartureDetection;
  /* VSS branch: Vehicle.ADAS.ObstacleDetection — Signals form Obstacle Sensor System. */
  part def Vehicle_ADAS_ObstacleDetection;
  /* VSS branch: Vehicle.ADAS.TCS — Traction Control System signals. */
  part def Vehicle_ADAS_TCS;
  /* VSS branch: Vehicle.Acceleration — Spatial acceleration. Axis definitions according to ISO 8855. */
  part def Vehicle_Acceleration;
  /* VSS branch: Vehicle.AngularVelocity — Spatial rotation. Axis definitions according to ISO 8855. */
  part def Vehicle_AngularVelocity;
  /* VSS branch: Vehicle.Body — All body components. */
  part def Vehicle_Body;
  /* VSS branch: Vehicle.Body.Hood — Hood status. Start position for Hood is Closed. */
  part def Vehicle_Body_Hood;
  /* VSS branch: Vehicle.Body.Horn — Horn signals. */
  part def Vehicle_Body_Horn;
  /* VSS branch: Vehicle.Body.Lights — Exterior lights. */
  part def Vehicle_Body_Lights;
  /* VSS branch: Vehicle.Body.Lights.Backup — Backup lights. */
  part def Vehicle_Body_Lights_Backup;
  /* VSS branch: Vehicle.Body.Lights.Beam — Beam lights. */
  part def Vehicle_Body_Lights_Beam;
  /* VSS branch: Vehicle.Body.Lights.Brake — Brake lights. */
  part def Vehicle_Body_Lights_Brake;
  /* VSS branch: Vehicle.Body.Lights.DirectionIndicator — Indicator lights. */
  part def Vehicle_Body_Lights_DirectionIndicator;
  /* VSS branch: Vehicle.Body.Lights.Fog — Fog lights. */
  part def Vehicle_Body_Lights_Fog;
  /* VSS branch: Vehicle.Body.Lights.Hazard — Hazard lights. */
  part def Vehicle_Body_Lights_Hazard;
  /* VSS branch: Vehicle.Body.Lights.LicensePlate — License plate lights. */
  part def Vehicle_Body_Lights_LicensePlate;
  /* VSS branch: Vehicle.Body.Lights.Parking — Parking lights. */
  part def Vehicle_Body_Lights_Parking;
  /* VSS branch: Vehicle.Body.Lights.Running — Daytime running lights (DRL). */
  part def Vehicle_Body_Lights_Running;
  /* VSS branch: Vehicle.Body.Mirrors — All mirrors. */
  part def Vehicle_Body_Mirrors;
  /* VSS branch: Vehicle.Body.Raindetection — Rain sensor signals. */
  part def Vehicle_Body_Raindetection;
  /* VSS branch: Vehicle.Body.Trunk — Trunk status. Start position for Trunk is Closed. */
  part def Vehicle_Body_Trunk;
  /* VSS branch: Vehicle.Body.Windshield — Windshield signals. */
  part def Vehicle_Body_Windshield;
  /* VSS branch: Vehicle.Body.Windshield.WasherFluid — Windshield washer fluid signals */
  part def Vehicle_Body_Windshield_WasherFluid;
  /* VSS branch: Vehicle.Body.Windshield.Wiping — Windshield wiper signals. */
  part def Vehicle_Body_Windshield_Wiping;
  /* VSS branch: Vehicle.Body.Windshield.Wiping.System — Signals to control behavior of wipers in detail. By default VSS expects only one instance. */
  part def Vehicle_Body_Windshield_Wiping_System;
  /* VSS branch: Vehicle.Cabin — All in-cabin components, including doors. */
  part def Vehicle_Cabin;
  /* VSS branch: Vehicle.Cabin.Convertible — Convertible roof. */
  part def Vehicle_Cabin_Convertible;
  /* VSS branch: Vehicle.Cabin.Door — All doors, including windows and switches. */
  part def Vehicle_Cabin_Door;
  /* VSS branch: Vehicle.Cabin.Door.Shade — Side window shade. Open = Retracted, Closed = Deployed. Start position for Shade is Open/Retracted. */
  part def Vehicle_Cabin_Door_Shade;
  /* VSS branch: Vehicle.Cabin.Door.Window — Door window status. Start position for Window is Closed. */
  part def Vehicle_Cabin_Door_Window;
  /* VSS branch: Vehicle.Cabin.HVAC — Climate control */
  part def Vehicle_Cabin_HVAC;
  /* VSS branch: Vehicle.Cabin.HVAC.Station — HVAC for single station in the vehicle */
  part def Vehicle_Cabin_HVAC_Station;
  /* VSS branch: Vehicle.Cabin.Infotainment — Infotainment system. */
  part def Vehicle_Cabin_Infotainment;
  /* VSS branch: Vehicle.Cabin.Infotainment.HMI — HMI related signals */
  part def Vehicle_Cabin_Infotainment_HMI;
  /* VSS branch: Vehicle.Cabin.Infotainment.Media — All Media actions */
  part def Vehicle_Cabin_Infotainment_Media;
  /* VSS branch: Vehicle.Cabin.Infotainment.Media.Played — Collection of signals updated in concert when a new media is played */
  part def Vehicle_Cabin_Infotainment_Media_Played;
  /* VSS branch: Vehicle.Cabin.Infotainment.Navigation — All navigation actions */
  part def Vehicle_Cabin_Infotainment_Navigation;
  /* VSS branch: Vehicle.Cabin.Infotainment.Navigation.DestinationSet — A navigation has been selected. */
  part def Vehicle_Cabin_Infotainment_Navigation_DestinationSet;
  /* VSS branch: Vehicle.Cabin.Infotainment.Navigation.Map — All map actions */
  part def Vehicle_Cabin_Infotainment_Navigation_Map;
  /* VSS branch: Vehicle.Cabin.Infotainment.SmartphoneProjection — All smartphone projection actions. */
  part def Vehicle_Cabin_Infotainment_SmartphoneProjection;
  /* VSS branch: Vehicle.Cabin.Infotainment.SmartphoneScreenMirroring — All smartphone screen mirroring actions. */
  part def Vehicle_Cabin_Infotainment_SmartphoneScreenMirroring;
  /* VSS branch: Vehicle.Cabin.Light — Light that is part of the Cabin. */
  part def Vehicle_Cabin_Light;
  /* VSS branch: Vehicle.Cabin.Light.AmbientLight — Decorative coloured light inside the cabin, usually mounted on the door, ceiling, etc. */
  part def Vehicle_Cabin_Light_AmbientLight;
  /* VSS branch: Vehicle.Cabin.Light.InteractiveLightBar — Decorative coloured light bar that supports effects, usually mounted on the dashboard (e.g. BMW i7 Interactive bar). */
  part def Vehicle_Cabin_Light_InteractiveLightBar;
  /* VSS branch: Vehicle.Cabin.Light.Spotlight — Spotlight for a specific area in the vehicle. */
  part def Vehicle_Cabin_Light_Spotlight;
  /* VSS branch: Vehicle.Cabin.RearShade — Rear window shade. Open = Retracted, Closed = Deployed. Start position for RearShade is Open/Retracted. */
  part def Vehicle_Cabin_RearShade;
  /* VSS branch: Vehicle.Cabin.RearviewMirror — Rear-view mirror. */
  part def Vehicle_Cabin_RearviewMirror;
  /* VSS branch: Vehicle.Cabin.Seat — All seats. */
  part def Vehicle_Cabin_Seat;
  /* VSS branch: Vehicle.Cabin.Seat.Airbag — Airbag signals. */
  part def Vehicle_Cabin_Seat_Airbag;
  /* VSS branch: Vehicle.Cabin.Seat.Backrest — Describes signals related to the backrest of the seat. */
  part def Vehicle_Cabin_Seat_Backrest;
  /* VSS branch: Vehicle.Cabin.Seat.Headrest — Headrest settings. */
  part def Vehicle_Cabin_Seat_Headrest;
  /* VSS branch: Vehicle.Cabin.Seat.Massage — Massage related information for the seat. */
  part def Vehicle_Cabin_Seat_Massage;
  /* VSS branch: Vehicle.Cabin.Seat.NeckScarf — NeckScarf settings. */
  part def Vehicle_Cabin_Seat_NeckScarf;
  /* VSS branch: Vehicle.Cabin.Seat.Seating — Describes signals related to the seat bottom of the seat. */
  part def Vehicle_Cabin_Seat_Seating;
  /* VSS branch: Vehicle.Cabin.Sunroof — Sun roof status. */
  part def Vehicle_Cabin_Sunroof;
  /* VSS branch: Vehicle.Cabin.Sunroof.Shade — Sun roof shade status. Open = Retracted, Closed = Deployed. Start position for Sunroof.Shade is Open/Retracted. */
  part def Vehicle_Cabin_Sunroof_Shade;
  /* VSS branch: Vehicle.Chassis — All data concerning steering, suspension, wheels, and brakes. */
  part def Vehicle_Chassis;
  /* VSS branch: Vehicle.Chassis.Accelerator — Accelerator signals */
  part def Vehicle_Chassis_Accelerator;
  /* VSS branch: Vehicle.Chassis.Axle — Axle signals */
  part def Vehicle_Chassis_Axle;
  /* VSS branch: Vehicle.Chassis.Axle.Wheel — Wheel signals for axle */
  part def Vehicle_Chassis_Axle_Wheel;
  /* VSS branch: Vehicle.Chassis.Axle.Wheel.Brake — Brake signals for wheel */
  part def Vehicle_Chassis_Axle_Wheel_Brake;
  /* VSS branch: Vehicle.Chassis.Axle.Wheel.Tire — Tire signals for wheel. */
  part def Vehicle_Chassis_Axle_Wheel_Tire;
  /* VSS branch: Vehicle.Chassis.Brake — Brake system signals */
  part def Vehicle_Chassis_Brake;
  /* VSS branch: Vehicle.Chassis.ParkingBrake — Parking brake signals */
  part def Vehicle_Chassis_ParkingBrake;
  /* VSS branch: Vehicle.Chassis.SteeringWheel — Steering wheel signals */
  part def Vehicle_Chassis_SteeringWheel;
  /* VSS branch: Vehicle.Connectivity — Connectivity data. */
  part def Vehicle_Connectivity;
  /* VSS branch: Vehicle.ControlUnit — Root of the control unit branch */
  part def Vehicle_ControlUnit;
  /* VSS branch: Vehicle.ControlUnit.Health — Health attributes and signals */
  part def Vehicle_ControlUnit_Health;
  /* VSS branch: Vehicle.ControlUnit.Health.Network — Network attributes and signals */
  part def Vehicle_ControlUnit_Health_Network;
  /* VSS branch: Vehicle.ControlUnit.Health.Network.CAN — CAN network attributes and signals */
  part def Vehicle_ControlUnit_Health_Network_CAN;
  /* VSS branch: Vehicle.ControlUnit.Health.Network.ETH — Ethernet network attributes and signals */
  part def Vehicle_ControlUnit_Health_Network_ETH;
  /* VSS branch: Vehicle.ControlUnit.Health.Resources — Resources attributes and signals */
  part def Vehicle_ControlUnit_Health_Resources;
  /* VSS branch: Vehicle.ControlUnit.Health.Resources.Utilization — Resources utilization branch */
  part def Vehicle_ControlUnit_Health_Resources_Utilization;
  /* VSS branch: Vehicle.ControlUnit.Health.SWSupervision — SW supervision attributes and signals */
  part def Vehicle_ControlUnit_Health_SWSupervision;
  /* VSS branch: Vehicle.CurrentLocation — The current latitude and longitude of the vehicle. */
  part def Vehicle_CurrentLocation;
  /* VSS branch: Vehicle.CurrentLocation.GNSSReceiver — Information on the GNSS receiver used for determining current location. */
  part def Vehicle_CurrentLocation_GNSSReceiver;
  /* VSS branch: Vehicle.CurrentLocation.GNSSReceiver.MountingPosition — Mounting position of GNSS receiver antenna relative to vehicle coordinate system. Axis definitions according to ISO 8855. Origin at center of (first) rear axle. */
  part def Vehicle_CurrentLocation_GNSSReceiver_MountingPosition;
  /* VSS branch: Vehicle.Diagnostics — Diagnostics data. */
  part def Vehicle_Diagnostics;
  /* VSS branch: Vehicle.Driver — Driver data. */
  part def Vehicle_Driver;
  /* VSS branch: Vehicle.Exterior — Information about exterior measured by vehicle. */
  part def Vehicle_Exterior;
  /* VSS branch: Vehicle.LowVoltageBattery — Signals related to low voltage battery. */
  part def Vehicle_LowVoltageBattery;
  /* VSS branch: Vehicle.MotionManagement — Motion Management Information. */
  part def Vehicle_MotionManagement;
  /* VSS branch: Vehicle.MotionManagement.Brake — MotionManagement related to braking (both frictions brakes and contribution from electric axles). */
  part def Vehicle_MotionManagement_Brake;
  /* VSS branch: Vehicle.MotionManagement.Brake.Axle — MotionManagement for brake actuation for a specific electric axle. */
  part def Vehicle_MotionManagement_Brake_Axle;
  /* VSS branch: Vehicle.MotionManagement.Brake.Axle.Wheel — MotionManagement signals for a specific wheel. */
  part def Vehicle_MotionManagement_Brake_Axle_Wheel;
  /* VSS branch: Vehicle.MotionManagement.ElectricAxle — MotionManagement for a specific electric axle. */
  part def Vehicle_MotionManagement_ElectricAxle;
  /* VSS branch: Vehicle.MotionManagement.Steering — MotionManagement related to steering. */
  part def Vehicle_MotionManagement_Steering;
  /* VSS branch: Vehicle.MotionManagement.Steering.Axle — MotionManagement related to a specific axle. */
  part def Vehicle_MotionManagement_Steering_Axle;
  /* VSS branch: Vehicle.MotionManagement.Steering.Axle.Row1 — MotionManagement related to front axle. */
  part def Vehicle_MotionManagement_Steering_Axle_Row1;
  /* VSS branch: Vehicle.MotionManagement.Steering.Axle.Row2 — MotionManagement related to rear axle. */
  part def Vehicle_MotionManagement_Steering_Axle_Row2;
  /* VSS branch: Vehicle.MotionManagement.Steering.SteeringWheel — MotionManagement related to steering wheel. */
  part def Vehicle_MotionManagement_Steering_SteeringWheel;
  /* VSS branch: Vehicle.MotionManagement.Suspension — MotionManagement related to suspension. */
  part def Vehicle_MotionManagement_Suspension;
  /* VSS branch: Vehicle.MotionManagement.Suspension.Axle — MotionManagement for suspension for a specific axle. */
  part def Vehicle_MotionManagement_Suspension_Axle;
  /* VSS branch: Vehicle.MotionManagement.Suspension.Axle.Wheel — MotionManagement signals for a specific wheel. */
  part def Vehicle_MotionManagement_Suspension_Axle_Wheel;
  /* VSS branch: Vehicle.Occupant — Occupant (Driver or Passenger) data. */
  part def Vehicle_Occupant;
  /* VSS branch: Vehicle.Occupant.HeadPosition — The current position of the driver head on vehicle axis according to ISO 23150:2023. */
  part def Vehicle_Occupant_HeadPosition;
  /* VSS branch: Vehicle.Occupant.Identifier — Identifier attributes based on OAuth 2.0. */
  part def Vehicle_Occupant_Identifier;
  /* VSS branch: Vehicle.Occupant.MidEyeGaze — Direction from mid eye position to object driver is looking at. */
  part def Vehicle_Occupant_MidEyeGaze;
  /* VSS branch: Vehicle.Orientation — Spatial orientation. Axis definitions according to ISO 8855. */
  part def Vehicle_Orientation;
  /* VSS branch: Vehicle.Powertrain — Powertrain data for battery management, etc. */
  part def Vehicle_Powertrain;
  /* VSS branch: Vehicle.Powertrain.CombustionEngine — Engine-specific data, stopping at the bell housing. */
  part def Vehicle_Powertrain_CombustionEngine;
  /* VSS branch: Vehicle.Powertrain.CombustionEngine.DieselExhaustFluid — Signals related to Diesel Exhaust Fluid (DEF). DEF is called AUS32 in ISO 22241. */
  part def Vehicle_Powertrain_CombustionEngine_DieselExhaustFluid;
  /* VSS branch: Vehicle.Powertrain.CombustionEngine.DieselParticulateFilter — Diesel Particulate Filter signals. */
  part def Vehicle_Powertrain_CombustionEngine_DieselParticulateFilter;
  /* VSS branch: Vehicle.Powertrain.CombustionEngine.EngineCoolant — Signals related to the engine coolant */
  part def Vehicle_Powertrain_CombustionEngine_EngineCoolant;
  /* VSS branch: Vehicle.Powertrain.CombustionEngine.EngineOil — Signals related to the engine oil */
  part def Vehicle_Powertrain_CombustionEngine_EngineOil;
  /* VSS branch: Vehicle.Powertrain.ElectricMotor — Electric Motor specific data. */
  part def Vehicle_Powertrain_ElectricMotor;
  /* VSS branch: Vehicle.Powertrain.ElectricMotor.EngineCoolant — Signals related to the engine coolant (if applicable). */
  part def Vehicle_Powertrain_ElectricMotor_EngineCoolant;
  /* VSS branch: Vehicle.Powertrain.FuelSystem — Fuel system data. */
  part def Vehicle_Powertrain_FuelSystem;
  /* VSS branch: Vehicle.Powertrain.RangeExtender — Extended Range Electric Vehicle (EREV) specific data. */
  part def Vehicle_Powertrain_RangeExtender;
  /* VSS branch: Vehicle.Powertrain.RangeExtender.ChargeDepleting — Signals related to Charge Depleting (CD) mode operation. */
  part def Vehicle_Powertrain_RangeExtender_ChargeDepleting;
  /* VSS branch: Vehicle.Powertrain.RangeExtender.ChargeSustaining — Signals related to Charge Sustaining (CS) mode operation. */
  part def Vehicle_Powertrain_RangeExtender_ChargeSustaining;
  /* VSS branch: Vehicle.Powertrain.TractionBattery — Battery Management data. */
  part def Vehicle_Powertrain_TractionBattery;
  /* VSS branch: Vehicle.Powertrain.TractionBattery.BatteryConditioning — Properties related to preparing the vehicle battery for charging or driving. */
  part def Vehicle_Powertrain_TractionBattery_BatteryConditioning;
  /* VSS branch: Vehicle.Powertrain.TractionBattery.CellVoltage — Voltage information for cells in the battery pack. */
  part def Vehicle_Powertrain_TractionBattery_CellVoltage;
  /* VSS branch: Vehicle.Powertrain.TractionBattery.Charging — Properties related to battery charging. */
  part def Vehicle_Powertrain_TractionBattery_Charging;
  /* VSS branch: Vehicle.Powertrain.TractionBattery.Charging.ChargeCurrent — Current charging current. */
  part def Vehicle_Powertrain_TractionBattery_Charging_ChargeCurrent;
  /* VSS branch: Vehicle.Powertrain.TractionBattery.Charging.ChargeVoltage — Current charging voltage, as measured at the charging inlet. */
  part def Vehicle_Powertrain_TractionBattery_Charging_ChargeVoltage;
  /* VSS branch: Vehicle.Powertrain.TractionBattery.Charging.ChargingPort — Properties related to a particular charging port available in the vehicle. */
  part def Vehicle_Powertrain_TractionBattery_Charging_ChargingPort;
  /* VSS branch: Vehicle.Powertrain.TractionBattery.Charging.Location — Location of last or current charging event. */
  part def Vehicle_Powertrain_TractionBattery_Charging_Location;
  /* VSS branch: Vehicle.Powertrain.TractionBattery.Charging.MaximumChargingCurrent — Maximum charging current that can be accepted by the system, as measured at the charging inlet. */
  part def Vehicle_Powertrain_TractionBattery_Charging_MaximumChargingCurrent;
  /* VSS branch: Vehicle.Powertrain.TractionBattery.Charging.Timer — Properties related to timing of battery charging sessions. */
  part def Vehicle_Powertrain_TractionBattery_Charging_Timer;
  /* VSS branch: Vehicle.Powertrain.TractionBattery.DCDC — Properties related to DC/DC converter converting high voltage (from high voltage battery) to vehicle low voltage (supply voltage, typically 12 Volts). */
  part def Vehicle_Powertrain_TractionBattery_DCDC;
  /* VSS branch: Vehicle.Powertrain.TractionBattery.StateOfCharge — Information on the state of charge of the vehicle's high voltage battery. */
  part def Vehicle_Powertrain_TractionBattery_StateOfCharge;
  /* VSS branch: Vehicle.Powertrain.TractionBattery.Temperature — Temperature Information for the battery pack. */
  part def Vehicle_Powertrain_TractionBattery_Temperature;
  /* VSS branch: Vehicle.Powertrain.Transmission — Transmission-specific data, stopping at the drive shafts. */
  part def Vehicle_Powertrain_Transmission;
  /* VSS branch: Vehicle.Safety — Safety-related derived signals for crash detection and emergency response. */
  part def Vehicle_Safety;
  /* VSS branch: Vehicle.Service — Service data. */
  part def Vehicle_Service;
  /* VSS branch: Vehicle.Trailer — Trailer signals. */
  part def Vehicle_Trailer;
  /* VSS branch: Vehicle.VehicleIdentification — Attributes that identify a vehicle. */
  part def Vehicle_VehicleIdentification;
  /* VSS branch: Vehicle.VersionVSS — Supported Version of VSS. */
  part def Vehicle_VersionVSS;
}

package SignalPathIndex {
  /* Human-readable aliases for SysML-safe signal definition names. */
  alias Vehicle_ADAS_ABS_IsEnabled for SignalDefinitions::Vehicle_ADAS_ABS_IsEnabled;
  alias Vehicle_ADAS_ABS_IsEngaged for SignalDefinitions::Vehicle_ADAS_ABS_IsEngaged;
  alias Vehicle_ADAS_ABS_IsError for SignalDefinitions::Vehicle_ADAS_ABS_IsError;
  alias Vehicle_ADAS_ActiveAutonomyLevel for SignalDefinitions::Vehicle_ADAS_ActiveAutonomyLevel;
  alias Vehicle_ADAS_CruiseControl_AdaptiveDistanceSet for SignalDefinitions::Vehicle_ADAS_CruiseControl_AdaptiveDistanceSet;
  alias Vehicle_ADAS_CruiseControl_AdaptiveIntervalSet for SignalDefinitions::Vehicle_ADAS_CruiseControl_AdaptiveIntervalSet;
  alias Vehicle_ADAS_CruiseControl_IsActive for SignalDefinitions::Vehicle_ADAS_CruiseControl_IsActive;
  alias Vehicle_ADAS_CruiseControl_IsAdaptive for SignalDefinitions::Vehicle_ADAS_CruiseControl_IsAdaptive;
  alias Vehicle_ADAS_CruiseControl_IsEnabled for SignalDefinitions::Vehicle_ADAS_CruiseControl_IsEnabled;
  alias Vehicle_ADAS_CruiseControl_IsError for SignalDefinitions::Vehicle_ADAS_CruiseControl_IsError;
  alias Vehicle_ADAS_CruiseControl_SpeedSet for SignalDefinitions::Vehicle_ADAS_CruiseControl_SpeedSet;
  alias Vehicle_ADAS_DMS_IsEnabled for SignalDefinitions::Vehicle_ADAS_DMS_IsEnabled;
  alias Vehicle_ADAS_DMS_IsError for SignalDefinitions::Vehicle_ADAS_DMS_IsError;
  alias Vehicle_ADAS_DMS_IsWarning for SignalDefinitions::Vehicle_ADAS_DMS_IsWarning;
  alias Vehicle_ADAS_EBA_IsEnabled for SignalDefinitions::Vehicle_ADAS_EBA_IsEnabled;
  alias Vehicle_ADAS_EBA_IsEngaged for SignalDefinitions::Vehicle_ADAS_EBA_IsEngaged;
  alias Vehicle_ADAS_EBA_IsError for SignalDefinitions::Vehicle_ADAS_EBA_IsError;
  alias Vehicle_ADAS_EBD_IsEnabled for SignalDefinitions::Vehicle_ADAS_EBD_IsEnabled;
  alias Vehicle_ADAS_EBD_IsEngaged for SignalDefinitions::Vehicle_ADAS_EBD_IsEngaged;
  alias Vehicle_ADAS_EBD_IsError for SignalDefinitions::Vehicle_ADAS_EBD_IsError;
  alias Vehicle_ADAS_ESC_IsEnabled for SignalDefinitions::Vehicle_ADAS_ESC_IsEnabled;
  alias Vehicle_ADAS_ESC_IsEngaged for SignalDefinitions::Vehicle_ADAS_ESC_IsEngaged;
  alias Vehicle_ADAS_ESC_IsError for SignalDefinitions::Vehicle_ADAS_ESC_IsError;
  alias Vehicle_ADAS_ESC_IsStrongCrossWindDetected for SignalDefinitions::Vehicle_ADAS_ESC_IsStrongCrossWindDetected;
  alias Vehicle_ADAS_ESC_RoadFriction_LowerBound for SignalDefinitions::Vehicle_ADAS_ESC_RoadFriction_LowerBound;
  alias Vehicle_ADAS_ESC_RoadFriction_MostProbable for SignalDefinitions::Vehicle_ADAS_ESC_RoadFriction_MostProbable;
  alias Vehicle_ADAS_ESC_RoadFriction_UpperBound for SignalDefinitions::Vehicle_ADAS_ESC_RoadFriction_UpperBound;
  alias Vehicle_ADAS_IsAutoPowerOptimize for SignalDefinitions::Vehicle_ADAS_IsAutoPowerOptimize;
  alias Vehicle_ADAS_LaneDepartureDetection_IsEnabled for SignalDefinitions::Vehicle_ADAS_LaneDepartureDetection_IsEnabled;
  alias Vehicle_ADAS_LaneDepartureDetection_IsError for SignalDefinitions::Vehicle_ADAS_LaneDepartureDetection_IsError;
  alias Vehicle_ADAS_LaneDepartureDetection_IsWarning for SignalDefinitions::Vehicle_ADAS_LaneDepartureDetection_IsWarning;
  alias Vehicle_ADAS_ObstacleDetection_Distance for SignalDefinitions::Vehicle_ADAS_ObstacleDetection_Distance;
  alias Vehicle_ADAS_ObstacleDetection_IsEnabled for SignalDefinitions::Vehicle_ADAS_ObstacleDetection_IsEnabled;
  alias Vehicle_ADAS_ObstacleDetection_IsError for SignalDefinitions::Vehicle_ADAS_ObstacleDetection_IsError;
  alias Vehicle_ADAS_ObstacleDetection_IsWarning for SignalDefinitions::Vehicle_ADAS_ObstacleDetection_IsWarning;
  alias Vehicle_ADAS_ObstacleDetection_TimeGap for SignalDefinitions::Vehicle_ADAS_ObstacleDetection_TimeGap;
  alias Vehicle_ADAS_ObstacleDetection_WarningType for SignalDefinitions::Vehicle_ADAS_ObstacleDetection_WarningType;
  alias Vehicle_ADAS_PowerOptimizeLevel for SignalDefinitions::Vehicle_ADAS_PowerOptimizeLevel;
  alias Vehicle_ADAS_SupportedAutonomyLevel for SignalDefinitions::Vehicle_ADAS_SupportedAutonomyLevel;
  alias Vehicle_ADAS_TCS_IsEnabled for SignalDefinitions::Vehicle_ADAS_TCS_IsEnabled;
  alias Vehicle_ADAS_TCS_IsEngaged for SignalDefinitions::Vehicle_ADAS_TCS_IsEngaged;
  alias Vehicle_ADAS_TCS_IsError for SignalDefinitions::Vehicle_ADAS_TCS_IsError;
  alias Vehicle_Acceleration_Lateral for SignalDefinitions::Vehicle_Acceleration_Lateral;
  alias Vehicle_Acceleration_Longitudinal for SignalDefinitions::Vehicle_Acceleration_Longitudinal;
  alias Vehicle_Acceleration_Vertical for SignalDefinitions::Vehicle_Acceleration_Vertical;
  alias Vehicle_AngularVelocity_Pitch for SignalDefinitions::Vehicle_AngularVelocity_Pitch;
  alias Vehicle_AngularVelocity_Roll for SignalDefinitions::Vehicle_AngularVelocity_Roll;
  alias Vehicle_AngularVelocity_Yaw for SignalDefinitions::Vehicle_AngularVelocity_Yaw;
  alias Vehicle_AverageSpeed for SignalDefinitions::Vehicle_AverageSpeed;
  alias Vehicle_Body_BodyType for SignalDefinitions::Vehicle_Body_BodyType;
  alias Vehicle_Body_Hood_IsOpen for SignalDefinitions::Vehicle_Body_Hood_IsOpen;
  alias Vehicle_Body_Hood_Position for SignalDefinitions::Vehicle_Body_Hood_Position;
  alias Vehicle_Body_Hood_Switch for SignalDefinitions::Vehicle_Body_Hood_Switch;
  alias Vehicle_Body_Horn_IsActive for SignalDefinitions::Vehicle_Body_Horn_IsActive;
  alias Vehicle_Body_IsAutoPowerOptimize for SignalDefinitions::Vehicle_Body_IsAutoPowerOptimize;
  alias Vehicle_Body_Lights_Backup_IsDefect for SignalDefinitions::Vehicle_Body_Lights_Backup_IsDefect;
  alias Vehicle_Body_Lights_Backup_IsOn for SignalDefinitions::Vehicle_Body_Lights_Backup_IsOn;
  alias Vehicle_Body_Lights_Beam_IsDefect for SignalDefinitions::Vehicle_Body_Lights_Beam_IsDefect;
  alias Vehicle_Body_Lights_Beam_IsOn for SignalDefinitions::Vehicle_Body_Lights_Beam_IsOn;
  alias Vehicle_Body_Lights_Brake_IsActive for SignalDefinitions::Vehicle_Body_Lights_Brake_IsActive;
  alias Vehicle_Body_Lights_Brake_IsDefect for SignalDefinitions::Vehicle_Body_Lights_Brake_IsDefect;
  alias Vehicle_Body_Lights_DirectionIndicator_IsDefect for SignalDefinitions::Vehicle_Body_Lights_DirectionIndicator_IsDefect;
  alias Vehicle_Body_Lights_DirectionIndicator_IsSignaling for SignalDefinitions::Vehicle_Body_Lights_DirectionIndicator_IsSignaling;
  alias Vehicle_Body_Lights_Fog_IsDefect for SignalDefinitions::Vehicle_Body_Lights_Fog_IsDefect;
  alias Vehicle_Body_Lights_Fog_IsOn for SignalDefinitions::Vehicle_Body_Lights_Fog_IsOn;
  alias Vehicle_Body_Lights_Hazard_IsDefect for SignalDefinitions::Vehicle_Body_Lights_Hazard_IsDefect;
  alias Vehicle_Body_Lights_Hazard_IsSignaling for SignalDefinitions::Vehicle_Body_Lights_Hazard_IsSignaling;
  alias Vehicle_Body_Lights_IsHighBeamSwitchOn for SignalDefinitions::Vehicle_Body_Lights_IsHighBeamSwitchOn;
  alias Vehicle_Body_Lights_LicensePlate_IsDefect for SignalDefinitions::Vehicle_Body_Lights_LicensePlate_IsDefect;
  alias Vehicle_Body_Lights_LicensePlate_IsOn for SignalDefinitions::Vehicle_Body_Lights_LicensePlate_IsOn;
  alias Vehicle_Body_Lights_LightSwitch for SignalDefinitions::Vehicle_Body_Lights_LightSwitch;
  alias Vehicle_Body_Lights_Parking_IsDefect for SignalDefinitions::Vehicle_Body_Lights_Parking_IsDefect;
  alias Vehicle_Body_Lights_Parking_IsOn for SignalDefinitions::Vehicle_Body_Lights_Parking_IsOn;
  alias Vehicle_Body_Lights_Running_IsDefect for SignalDefinitions::Vehicle_Body_Lights_Running_IsDefect;
  alias Vehicle_Body_Lights_Running_IsOn for SignalDefinitions::Vehicle_Body_Lights_Running_IsOn;
  alias Vehicle_Body_Mirrors_IsFolded for SignalDefinitions::Vehicle_Body_Mirrors_IsFolded;
  alias Vehicle_Body_Mirrors_IsHeatingOn for SignalDefinitions::Vehicle_Body_Mirrors_IsHeatingOn;
  alias Vehicle_Body_Mirrors_IsLocked for SignalDefinitions::Vehicle_Body_Mirrors_IsLocked;
  alias Vehicle_Body_Mirrors_Pan for SignalDefinitions::Vehicle_Body_Mirrors_Pan;
  alias Vehicle_Body_Mirrors_Tilt for SignalDefinitions::Vehicle_Body_Mirrors_Tilt;
  alias Vehicle_Body_Mirrors_Yaw for SignalDefinitions::Vehicle_Body_Mirrors_Yaw;
  alias Vehicle_Body_PowerOptimizeLevel for SignalDefinitions::Vehicle_Body_PowerOptimizeLevel;
  alias Vehicle_Body_Raindetection_Intensity for SignalDefinitions::Vehicle_Body_Raindetection_Intensity;
  alias Vehicle_Body_RearMainSpoilerPosition for SignalDefinitions::Vehicle_Body_RearMainSpoilerPosition;
  alias Vehicle_Body_Trunk_IsLightOn for SignalDefinitions::Vehicle_Body_Trunk_IsLightOn;
  alias Vehicle_Body_Trunk_IsLocked for SignalDefinitions::Vehicle_Body_Trunk_IsLocked;
  alias Vehicle_Body_Trunk_IsOpen for SignalDefinitions::Vehicle_Body_Trunk_IsOpen;
  alias Vehicle_Body_Trunk_Position for SignalDefinitions::Vehicle_Body_Trunk_Position;
  alias Vehicle_Body_Trunk_Switch for SignalDefinitions::Vehicle_Body_Trunk_Switch;
  alias Vehicle_Body_Windshield_IsHeatingOn for SignalDefinitions::Vehicle_Body_Windshield_IsHeatingOn;
  alias Vehicle_Body_Windshield_WasherFluid_IsLevelLow for SignalDefinitions::Vehicle_Body_Windshield_WasherFluid_IsLevelLow;
  alias Vehicle_Body_Windshield_WasherFluid_Level for SignalDefinitions::Vehicle_Body_Windshield_WasherFluid_Level;
  alias Vehicle_Body_Windshield_Wiping_Intensity for SignalDefinitions::Vehicle_Body_Windshield_Wiping_Intensity;
  alias Vehicle_Body_Windshield_Wiping_IsWipersWorn for SignalDefinitions::Vehicle_Body_Windshield_Wiping_IsWipersWorn;
  alias Vehicle_Body_Windshield_Wiping_Mode for SignalDefinitions::Vehicle_Body_Windshield_Wiping_Mode;
  alias Vehicle_Body_Windshield_Wiping_System_ActualPosition for SignalDefinitions::Vehicle_Body_Windshield_Wiping_System_ActualPosition;
  alias Vehicle_Body_Windshield_Wiping_System_DriveCurrent for SignalDefinitions::Vehicle_Body_Windshield_Wiping_System_DriveCurrent;
  alias Vehicle_Body_Windshield_Wiping_System_Frequency for SignalDefinitions::Vehicle_Body_Windshield_Wiping_System_Frequency;
  alias Vehicle_Body_Windshield_Wiping_System_IsBlocked for SignalDefinitions::Vehicle_Body_Windshield_Wiping_System_IsBlocked;
  alias Vehicle_Body_Windshield_Wiping_System_IsEndingWipeCycle for SignalDefinitions::Vehicle_Body_Windshield_Wiping_System_IsEndingWipeCycle;
  alias Vehicle_Body_Windshield_Wiping_System_IsOverheated for SignalDefinitions::Vehicle_Body_Windshield_Wiping_System_IsOverheated;
  alias Vehicle_Body_Windshield_Wiping_System_IsPositionReached for SignalDefinitions::Vehicle_Body_Windshield_Wiping_System_IsPositionReached;
  alias Vehicle_Body_Windshield_Wiping_System_IsWiperError for SignalDefinitions::Vehicle_Body_Windshield_Wiping_System_IsWiperError;
  alias Vehicle_Body_Windshield_Wiping_System_IsWiping for SignalDefinitions::Vehicle_Body_Windshield_Wiping_System_IsWiping;
  alias Vehicle_Body_Windshield_Wiping_System_Mode for SignalDefinitions::Vehicle_Body_Windshield_Wiping_System_Mode;
  alias Vehicle_Body_Windshield_Wiping_System_TargetPosition for SignalDefinitions::Vehicle_Body_Windshield_Wiping_System_TargetPosition;
  alias Vehicle_Body_Windshield_Wiping_WiperWear for SignalDefinitions::Vehicle_Body_Windshield_Wiping_WiperWear;
  alias Vehicle_Cabin_Convertible_Status for SignalDefinitions::Vehicle_Cabin_Convertible_Status;
  alias Vehicle_Cabin_Door_IsChildLockActive for SignalDefinitions::Vehicle_Cabin_Door_IsChildLockActive;
  alias Vehicle_Cabin_Door_IsLocked for SignalDefinitions::Vehicle_Cabin_Door_IsLocked;
  alias Vehicle_Cabin_Door_IsOpen for SignalDefinitions::Vehicle_Cabin_Door_IsOpen;
  alias Vehicle_Cabin_Door_Position for SignalDefinitions::Vehicle_Cabin_Door_Position;
  alias Vehicle_Cabin_Door_Shade_IsOpen for SignalDefinitions::Vehicle_Cabin_Door_Shade_IsOpen;
  alias Vehicle_Cabin_Door_Shade_Position for SignalDefinitions::Vehicle_Cabin_Door_Shade_Position;
  alias Vehicle_Cabin_Door_Shade_Switch for SignalDefinitions::Vehicle_Cabin_Door_Shade_Switch;
  alias Vehicle_Cabin_Door_Switch for SignalDefinitions::Vehicle_Cabin_Door_Switch;
  alias Vehicle_Cabin_Door_Window_IsOpen for SignalDefinitions::Vehicle_Cabin_Door_Window_IsOpen;
  alias Vehicle_Cabin_Door_Window_Position for SignalDefinitions::Vehicle_Cabin_Door_Window_Position;
  alias Vehicle_Cabin_Door_Window_Switch for SignalDefinitions::Vehicle_Cabin_Door_Window_Switch;
  alias Vehicle_Cabin_DoorCount for SignalDefinitions::Vehicle_Cabin_DoorCount;
  alias Vehicle_Cabin_DriverPosition for SignalDefinitions::Vehicle_Cabin_DriverPosition;
  alias Vehicle_Cabin_HVAC_AmbientAirTemperature for SignalDefinitions::Vehicle_Cabin_HVAC_AmbientAirTemperature;
  alias Vehicle_Cabin_HVAC_IsAirConditioningActive for SignalDefinitions::Vehicle_Cabin_HVAC_IsAirConditioningActive;
  alias Vehicle_Cabin_HVAC_IsAutoPowerOptimize for SignalDefinitions::Vehicle_Cabin_HVAC_IsAutoPowerOptimize;
  alias Vehicle_Cabin_HVAC_IsFrontDefrosterActive for SignalDefinitions::Vehicle_Cabin_HVAC_IsFrontDefrosterActive;
  alias Vehicle_Cabin_HVAC_IsRearDefrosterActive for SignalDefinitions::Vehicle_Cabin_HVAC_IsRearDefrosterActive;
  alias Vehicle_Cabin_HVAC_IsRecirculationActive for SignalDefinitions::Vehicle_Cabin_HVAC_IsRecirculationActive;
  alias Vehicle_Cabin_HVAC_PowerOptimizeLevel for SignalDefinitions::Vehicle_Cabin_HVAC_PowerOptimizeLevel;
  alias Vehicle_Cabin_HVAC_Station_AirDistribution for SignalDefinitions::Vehicle_Cabin_HVAC_Station_AirDistribution;
  alias Vehicle_Cabin_HVAC_Station_FanSpeed for SignalDefinitions::Vehicle_Cabin_HVAC_Station_FanSpeed;
  alias Vehicle_Cabin_HVAC_Station_Temperature for SignalDefinitions::Vehicle_Cabin_HVAC_Station_Temperature;
  alias Vehicle_Cabin_Infotainment_HMI_Brightness for SignalDefinitions::Vehicle_Cabin_Infotainment_HMI_Brightness;
  alias Vehicle_Cabin_Infotainment_HMI_CurrentLanguage for SignalDefinitions::Vehicle_Cabin_Infotainment_HMI_CurrentLanguage;
  alias Vehicle_Cabin_Infotainment_HMI_DateFormat for SignalDefinitions::Vehicle_Cabin_Infotainment_HMI_DateFormat;
  alias Vehicle_Cabin_Infotainment_HMI_DayNightMode for SignalDefinitions::Vehicle_Cabin_Infotainment_HMI_DayNightMode;
  alias Vehicle_Cabin_Infotainment_HMI_DisplayOffDuration for SignalDefinitions::Vehicle_Cabin_Infotainment_HMI_DisplayOffDuration;
  alias Vehicle_Cabin_Infotainment_HMI_DistanceUnit for SignalDefinitions::Vehicle_Cabin_Infotainment_HMI_DistanceUnit;
  alias Vehicle_Cabin_Infotainment_HMI_EVEconomyUnits for SignalDefinitions::Vehicle_Cabin_Infotainment_HMI_EVEconomyUnits;
  alias Vehicle_Cabin_Infotainment_HMI_EVEnergyUnits for SignalDefinitions::Vehicle_Cabin_Infotainment_HMI_EVEnergyUnits;
  alias Vehicle_Cabin_Infotainment_HMI_FontSize for SignalDefinitions::Vehicle_Cabin_Infotainment_HMI_FontSize;
  alias Vehicle_Cabin_Infotainment_HMI_FuelEconomyUnits for SignalDefinitions::Vehicle_Cabin_Infotainment_HMI_FuelEconomyUnits;
  alias Vehicle_Cabin_Infotainment_HMI_FuelVolumeUnit for SignalDefinitions::Vehicle_Cabin_Infotainment_HMI_FuelVolumeUnit;
  alias Vehicle_Cabin_Infotainment_HMI_IsScreenAlwaysOn for SignalDefinitions::Vehicle_Cabin_Infotainment_HMI_IsScreenAlwaysOn;
  alias Vehicle_Cabin_Infotainment_HMI_LastActionTime for SignalDefinitions::Vehicle_Cabin_Infotainment_HMI_LastActionTime;
  alias Vehicle_Cabin_Infotainment_HMI_SpeedUnit for SignalDefinitions::Vehicle_Cabin_Infotainment_HMI_SpeedUnit;
  alias Vehicle_Cabin_Infotainment_HMI_TemperatureUnit for SignalDefinitions::Vehicle_Cabin_Infotainment_HMI_TemperatureUnit;
  alias Vehicle_Cabin_Infotainment_HMI_TimeFormat for SignalDefinitions::Vehicle_Cabin_Infotainment_HMI_TimeFormat;
  alias Vehicle_Cabin_Infotainment_HMI_TirePressureUnit for SignalDefinitions::Vehicle_Cabin_Infotainment_HMI_TirePressureUnit;
  alias Vehicle_Cabin_Infotainment_IsAutoPowerOptimize for SignalDefinitions::Vehicle_Cabin_Infotainment_IsAutoPowerOptimize;
  alias Vehicle_Cabin_Infotainment_Media_Action for SignalDefinitions::Vehicle_Cabin_Infotainment_Media_Action;
  alias Vehicle_Cabin_Infotainment_Media_DeclinedURI for SignalDefinitions::Vehicle_Cabin_Infotainment_Media_DeclinedURI;
  alias Vehicle_Cabin_Infotainment_Media_Played_Album for SignalDefinitions::Vehicle_Cabin_Infotainment_Media_Played_Album;
  alias Vehicle_Cabin_Infotainment_Media_Played_Artist for SignalDefinitions::Vehicle_Cabin_Infotainment_Media_Played_Artist;
  alias Vehicle_Cabin_Infotainment_Media_Played_Genre for SignalDefinitions::Vehicle_Cabin_Infotainment_Media_Played_Genre;
  alias Vehicle_Cabin_Infotainment_Media_Played_PlaybackRate for SignalDefinitions::Vehicle_Cabin_Infotainment_Media_Played_PlaybackRate;
  alias Vehicle_Cabin_Infotainment_Media_Played_Source for SignalDefinitions::Vehicle_Cabin_Infotainment_Media_Played_Source;
  alias Vehicle_Cabin_Infotainment_Media_Played_Track for SignalDefinitions::Vehicle_Cabin_Infotainment_Media_Played_Track;
  alias Vehicle_Cabin_Infotainment_Media_Played_URI for SignalDefinitions::Vehicle_Cabin_Infotainment_Media_Played_URI;
  alias Vehicle_Cabin_Infotainment_Media_SelectedURI for SignalDefinitions::Vehicle_Cabin_Infotainment_Media_SelectedURI;
  alias Vehicle_Cabin_Infotainment_Media_Volume for SignalDefinitions::Vehicle_Cabin_Infotainment_Media_Volume;
  alias Vehicle_Cabin_Infotainment_Navigation_DestinationSet_Latitude for SignalDefinitions::Vehicle_Cabin_Infotainment_Navigation_DestinationSet_Latitude;
  alias Vehicle_Cabin_Infotainment_Navigation_DestinationSet_Longitude for SignalDefinitions::Vehicle_Cabin_Infotainment_Navigation_DestinationSet_Longitude;
  alias Vehicle_Cabin_Infotainment_Navigation_GuidanceVoice for SignalDefinitions::Vehicle_Cabin_Infotainment_Navigation_GuidanceVoice;
  alias Vehicle_Cabin_Infotainment_Navigation_Map_IsAutoScaleModeUsed for SignalDefinitions::Vehicle_Cabin_Infotainment_Navigation_Map_IsAutoScaleModeUsed;
  alias Vehicle_Cabin_Infotainment_Navigation_Mute for SignalDefinitions::Vehicle_Cabin_Infotainment_Navigation_Mute;
  alias Vehicle_Cabin_Infotainment_Navigation_Volume for SignalDefinitions::Vehicle_Cabin_Infotainment_Navigation_Volume;
  alias Vehicle_Cabin_Infotainment_PowerOptimizeLevel for SignalDefinitions::Vehicle_Cabin_Infotainment_PowerOptimizeLevel;
  alias Vehicle_Cabin_Infotainment_SmartphoneProjection_Active for SignalDefinitions::Vehicle_Cabin_Infotainment_SmartphoneProjection_Active;
  alias Vehicle_Cabin_Infotainment_SmartphoneProjection_Source for SignalDefinitions::Vehicle_Cabin_Infotainment_SmartphoneProjection_Source;
  alias Vehicle_Cabin_Infotainment_SmartphoneProjection_SupportedMode for SignalDefinitions::Vehicle_Cabin_Infotainment_SmartphoneProjection_SupportedMode;
  alias Vehicle_Cabin_Infotainment_SmartphoneScreenMirroring_Active for SignalDefinitions::Vehicle_Cabin_Infotainment_SmartphoneScreenMirroring_Active;
  alias Vehicle_Cabin_Infotainment_SmartphoneScreenMirroring_Source for SignalDefinitions::Vehicle_Cabin_Infotainment_SmartphoneScreenMirroring_Source;
  alias Vehicle_Cabin_IsAutoPowerOptimize for SignalDefinitions::Vehicle_Cabin_IsAutoPowerOptimize;
  alias Vehicle_Cabin_IsWindowChildLockEngaged for SignalDefinitions::Vehicle_Cabin_IsWindowChildLockEngaged;
  alias Vehicle_Cabin_Light_AmbientLight_Color for SignalDefinitions::Vehicle_Cabin_Light_AmbientLight_Color;
  alias Vehicle_Cabin_Light_AmbientLight_Intensity for SignalDefinitions::Vehicle_Cabin_Light_AmbientLight_Intensity;
  alias Vehicle_Cabin_Light_AmbientLight_IsLightOn for SignalDefinitions::Vehicle_Cabin_Light_AmbientLight_IsLightOn;
  alias Vehicle_Cabin_Light_InteractiveLightBar_Color for SignalDefinitions::Vehicle_Cabin_Light_InteractiveLightBar_Color;
  alias Vehicle_Cabin_Light_InteractiveLightBar_Effect for SignalDefinitions::Vehicle_Cabin_Light_InteractiveLightBar_Effect;
  alias Vehicle_Cabin_Light_InteractiveLightBar_Intensity for SignalDefinitions::Vehicle_Cabin_Light_InteractiveLightBar_Intensity;
  alias Vehicle_Cabin_Light_InteractiveLightBar_IsLightOn for SignalDefinitions::Vehicle_Cabin_Light_InteractiveLightBar_IsLightOn;
  alias Vehicle_Cabin_Light_IsDomeOn for SignalDefinitions::Vehicle_Cabin_Light_IsDomeOn;
  alias Vehicle_Cabin_Light_IsGloveBoxOn for SignalDefinitions::Vehicle_Cabin_Light_IsGloveBoxOn;
  alias Vehicle_Cabin_Light_PerceivedAmbientLight for SignalDefinitions::Vehicle_Cabin_Light_PerceivedAmbientLight;
  alias Vehicle_Cabin_Light_Spotlight_Color for SignalDefinitions::Vehicle_Cabin_Light_Spotlight_Color;
  alias Vehicle_Cabin_Light_Spotlight_Intensity for SignalDefinitions::Vehicle_Cabin_Light_Spotlight_Intensity;
  alias Vehicle_Cabin_Light_Spotlight_IsLightOn for SignalDefinitions::Vehicle_Cabin_Light_Spotlight_IsLightOn;
  alias Vehicle_Cabin_PowerOptimizeLevel for SignalDefinitions::Vehicle_Cabin_PowerOptimizeLevel;
  alias Vehicle_Cabin_RearShade_IsOpen for SignalDefinitions::Vehicle_Cabin_RearShade_IsOpen;
  alias Vehicle_Cabin_RearShade_Position for SignalDefinitions::Vehicle_Cabin_RearShade_Position;
  alias Vehicle_Cabin_RearShade_Switch for SignalDefinitions::Vehicle_Cabin_RearShade_Switch;
  alias Vehicle_Cabin_RearviewMirror_DimmingLevel for SignalDefinitions::Vehicle_Cabin_RearviewMirror_DimmingLevel;
  alias Vehicle_Cabin_Seat_Airbag_IsDeployed for SignalDefinitions::Vehicle_Cabin_Seat_Airbag_IsDeployed;
  alias Vehicle_Cabin_Seat_Airbag_IsEnabled for SignalDefinitions::Vehicle_Cabin_Seat_Airbag_IsEnabled;
  alias Vehicle_Cabin_Seat_Backrest_BottomLumbarSupport for SignalDefinitions::Vehicle_Cabin_Seat_Backrest_BottomLumbarSupport;
  alias Vehicle_Cabin_Seat_Backrest_HeatingCooling for SignalDefinitions::Vehicle_Cabin_Seat_Backrest_HeatingCooling;
  alias Vehicle_Cabin_Seat_Backrest_IsLessLumbarSupportSwitchEngaged for SignalDefinitions::Vehicle_Cabin_Seat_Backrest_IsLessLumbarSupportSwitchEngaged;
  alias Vehicle_Cabin_Seat_Backrest_IsLessSideBolsterSupportSwitchEngaged for SignalDefinitions::Vehicle_Cabin_Seat_Backrest_IsLessSideBolsterSupportSwitchEngaged;
  alias Vehicle_Cabin_Seat_Backrest_IsLumbarDownSwitchEngaged for SignalDefinitions::Vehicle_Cabin_Seat_Backrest_IsLumbarDownSwitchEngaged;
  alias Vehicle_Cabin_Seat_Backrest_IsLumbarUpSwitchEngaged for SignalDefinitions::Vehicle_Cabin_Seat_Backrest_IsLumbarUpSwitchEngaged;
  alias Vehicle_Cabin_Seat_Backrest_IsMoreLumbarSupportSwitchEngaged for SignalDefinitions::Vehicle_Cabin_Seat_Backrest_IsMoreLumbarSupportSwitchEngaged;
  alias Vehicle_Cabin_Seat_Backrest_IsMoreSideBolsterSupportSwitchEngaged for SignalDefinitions::Vehicle_Cabin_Seat_Backrest_IsMoreSideBolsterSupportSwitchEngaged;
  alias Vehicle_Cabin_Seat_Backrest_IsReclineBackwardSwitchEngaged for SignalDefinitions::Vehicle_Cabin_Seat_Backrest_IsReclineBackwardSwitchEngaged;
  alias Vehicle_Cabin_Seat_Backrest_IsReclineForwardSwitchEngaged for SignalDefinitions::Vehicle_Cabin_Seat_Backrest_IsReclineForwardSwitchEngaged;
  alias Vehicle_Cabin_Seat_Backrest_LumbarHeight for SignalDefinitions::Vehicle_Cabin_Seat_Backrest_LumbarHeight;
  alias Vehicle_Cabin_Seat_Backrest_LumbarSupport for SignalDefinitions::Vehicle_Cabin_Seat_Backrest_LumbarSupport;
  alias Vehicle_Cabin_Seat_Backrest_MidLumbarSupport for SignalDefinitions::Vehicle_Cabin_Seat_Backrest_MidLumbarSupport;
  alias Vehicle_Cabin_Seat_Backrest_Recline for SignalDefinitions::Vehicle_Cabin_Seat_Backrest_Recline;
  alias Vehicle_Cabin_Seat_Backrest_SideBolsterSupport for SignalDefinitions::Vehicle_Cabin_Seat_Backrest_SideBolsterSupport;
  alias Vehicle_Cabin_Seat_Backrest_SideBolsterSupportLeft for SignalDefinitions::Vehicle_Cabin_Seat_Backrest_SideBolsterSupportLeft;
  alias Vehicle_Cabin_Seat_Backrest_SideBolsterSupportRight for SignalDefinitions::Vehicle_Cabin_Seat_Backrest_SideBolsterSupportRight;
  alias Vehicle_Cabin_Seat_Backrest_TopLumbarSupport for SignalDefinitions::Vehicle_Cabin_Seat_Backrest_TopLumbarSupport;
  alias Vehicle_Cabin_Seat_Backrest_UpperShoulderSupport for SignalDefinitions::Vehicle_Cabin_Seat_Backrest_UpperShoulderSupport;
  alias Vehicle_Cabin_Seat_Headrest_Angle for SignalDefinitions::Vehicle_Cabin_Seat_Headrest_Angle;
  alias Vehicle_Cabin_Seat_Headrest_Height for SignalDefinitions::Vehicle_Cabin_Seat_Headrest_Height;
  alias Vehicle_Cabin_Seat_Headrest_IsBackwardSwitchEngaged for SignalDefinitions::Vehicle_Cabin_Seat_Headrest_IsBackwardSwitchEngaged;
  alias Vehicle_Cabin_Seat_Headrest_IsDownSwitchEngaged for SignalDefinitions::Vehicle_Cabin_Seat_Headrest_IsDownSwitchEngaged;
  alias Vehicle_Cabin_Seat_Headrest_IsForwardSwitchEngaged for SignalDefinitions::Vehicle_Cabin_Seat_Headrest_IsForwardSwitchEngaged;
  alias Vehicle_Cabin_Seat_Headrest_IsUpSwitchEngaged for SignalDefinitions::Vehicle_Cabin_Seat_Headrest_IsUpSwitchEngaged;
  alias Vehicle_Cabin_Seat_HeatingCooling for SignalDefinitions::Vehicle_Cabin_Seat_HeatingCooling;
  alias Vehicle_Cabin_Seat_Height for SignalDefinitions::Vehicle_Cabin_Seat_Height;
  alias Vehicle_Cabin_Seat_IsBackwardSwitchEngaged for SignalDefinitions::Vehicle_Cabin_Seat_IsBackwardSwitchEngaged;
  alias Vehicle_Cabin_Seat_IsBelted for SignalDefinitions::Vehicle_Cabin_Seat_IsBelted;
  alias Vehicle_Cabin_Seat_IsCoolerSwitchEngaged for SignalDefinitions::Vehicle_Cabin_Seat_IsCoolerSwitchEngaged;
  alias Vehicle_Cabin_Seat_IsDecreaseMassageLevelSwitchEngaged for SignalDefinitions::Vehicle_Cabin_Seat_IsDecreaseMassageLevelSwitchEngaged;
  alias Vehicle_Cabin_Seat_IsDownSwitchEngaged for SignalDefinitions::Vehicle_Cabin_Seat_IsDownSwitchEngaged;
  alias Vehicle_Cabin_Seat_IsForwardSwitchEngaged for SignalDefinitions::Vehicle_Cabin_Seat_IsForwardSwitchEngaged;
  alias Vehicle_Cabin_Seat_IsIncreaseMassageLevelSwitchEngaged for SignalDefinitions::Vehicle_Cabin_Seat_IsIncreaseMassageLevelSwitchEngaged;
  alias Vehicle_Cabin_Seat_IsTiltBackwardSwitchEngaged for SignalDefinitions::Vehicle_Cabin_Seat_IsTiltBackwardSwitchEngaged;
  alias Vehicle_Cabin_Seat_IsTiltForwardSwitchEngaged for SignalDefinitions::Vehicle_Cabin_Seat_IsTiltForwardSwitchEngaged;
  alias Vehicle_Cabin_Seat_IsUpSwitchEngaged for SignalDefinitions::Vehicle_Cabin_Seat_IsUpSwitchEngaged;
  alias Vehicle_Cabin_Seat_IsWarmerSwitchEngaged for SignalDefinitions::Vehicle_Cabin_Seat_IsWarmerSwitchEngaged;
  alias Vehicle_Cabin_Seat_Massage_IsAvailable for SignalDefinitions::Vehicle_Cabin_Seat_Massage_IsAvailable;
  alias Vehicle_Cabin_Seat_Massage_Level for SignalDefinitions::Vehicle_Cabin_Seat_Massage_Level;
  alias Vehicle_Cabin_Seat_Massage_Status for SignalDefinitions::Vehicle_Cabin_Seat_Massage_Status;
  alias Vehicle_Cabin_Seat_Massage_SupportedTypes for SignalDefinitions::Vehicle_Cabin_Seat_Massage_SupportedTypes;
  alias Vehicle_Cabin_Seat_Massage_TypeActive for SignalDefinitions::Vehicle_Cabin_Seat_Massage_TypeActive;
  alias Vehicle_Cabin_Seat_NeckScarf_FanSpeed for SignalDefinitions::Vehicle_Cabin_Seat_NeckScarf_FanSpeed;
  alias Vehicle_Cabin_Seat_NeckScarf_HeatingCooling for SignalDefinitions::Vehicle_Cabin_Seat_NeckScarf_HeatingCooling;
  alias Vehicle_Cabin_Seat_OccupancyStatus for SignalDefinitions::Vehicle_Cabin_Seat_OccupancyStatus;
  alias Vehicle_Cabin_Seat_Position for SignalDefinitions::Vehicle_Cabin_Seat_Position;
  alias Vehicle_Cabin_Seat_SeatBeltHeight for SignalDefinitions::Vehicle_Cabin_Seat_SeatBeltHeight;
  alias Vehicle_Cabin_Seat_Seating_HeatingCooling for SignalDefinitions::Vehicle_Cabin_Seat_Seating_HeatingCooling;
  alias Vehicle_Cabin_Seat_Seating_IsBackwardSwitchEngaged for SignalDefinitions::Vehicle_Cabin_Seat_Seating_IsBackwardSwitchEngaged;
  alias Vehicle_Cabin_Seat_Seating_IsForwardSwitchEngaged for SignalDefinitions::Vehicle_Cabin_Seat_Seating_IsForwardSwitchEngaged;
  alias Vehicle_Cabin_Seat_Seating_Length for SignalDefinitions::Vehicle_Cabin_Seat_Seating_Length;
  alias Vehicle_Cabin_Seat_Seating_SideBolsterSupportLeft for SignalDefinitions::Vehicle_Cabin_Seat_Seating_SideBolsterSupportLeft;
  alias Vehicle_Cabin_Seat_Seating_SideBolsterSupportRight for SignalDefinitions::Vehicle_Cabin_Seat_Seating_SideBolsterSupportRight;
  alias Vehicle_Cabin_Seat_Tilt for SignalDefinitions::Vehicle_Cabin_Seat_Tilt;
  alias Vehicle_Cabin_SeatPosCount for SignalDefinitions::Vehicle_Cabin_SeatPosCount;
  alias Vehicle_Cabin_SeatRowCount for SignalDefinitions::Vehicle_Cabin_SeatRowCount;
  alias Vehicle_Cabin_Sunroof_Position for SignalDefinitions::Vehicle_Cabin_Sunroof_Position;
  alias Vehicle_Cabin_Sunroof_Shade_IsOpen for SignalDefinitions::Vehicle_Cabin_Sunroof_Shade_IsOpen;
  alias Vehicle_Cabin_Sunroof_Shade_Position for SignalDefinitions::Vehicle_Cabin_Sunroof_Shade_Position;
  alias Vehicle_Cabin_Sunroof_Shade_Switch for SignalDefinitions::Vehicle_Cabin_Sunroof_Shade_Switch;
  alias Vehicle_Cabin_Sunroof_Switch for SignalDefinitions::Vehicle_Cabin_Sunroof_Switch;
  alias Vehicle_CargoVolume for SignalDefinitions::Vehicle_CargoVolume;
  alias Vehicle_Chassis_Accelerator_PedalPosition for SignalDefinitions::Vehicle_Chassis_Accelerator_PedalPosition;
  alias Vehicle_Chassis_Axle_AxleWidth for SignalDefinitions::Vehicle_Chassis_Axle_AxleWidth;
  alias Vehicle_Chassis_Axle_SteeringAngle for SignalDefinitions::Vehicle_Chassis_Axle_SteeringAngle;
  alias Vehicle_Chassis_Axle_TireAspectRatio for SignalDefinitions::Vehicle_Chassis_Axle_TireAspectRatio;
  alias Vehicle_Chassis_Axle_TireDiameter for SignalDefinitions::Vehicle_Chassis_Axle_TireDiameter;
  alias Vehicle_Chassis_Axle_TireWidth for SignalDefinitions::Vehicle_Chassis_Axle_TireWidth;
  alias Vehicle_Chassis_Axle_Torque for SignalDefinitions::Vehicle_Chassis_Axle_Torque;
  alias Vehicle_Chassis_Axle_TrackWidth for SignalDefinitions::Vehicle_Chassis_Axle_TrackWidth;
  alias Vehicle_Chassis_Axle_TreadWidth for SignalDefinitions::Vehicle_Chassis_Axle_TreadWidth;
  alias Vehicle_Chassis_Axle_Wheel_AngularSpeed for SignalDefinitions::Vehicle_Chassis_Axle_Wheel_AngularSpeed;
  alias Vehicle_Chassis_Axle_Wheel_Brake_FluidLevel for SignalDefinitions::Vehicle_Chassis_Axle_Wheel_Brake_FluidLevel;
  alias Vehicle_Chassis_Axle_Wheel_Brake_IsBrakesWorn for SignalDefinitions::Vehicle_Chassis_Axle_Wheel_Brake_IsBrakesWorn;
  alias Vehicle_Chassis_Axle_Wheel_Brake_IsFluidLevelLow for SignalDefinitions::Vehicle_Chassis_Axle_Wheel_Brake_IsFluidLevelLow;
  alias Vehicle_Chassis_Axle_Wheel_Brake_PadWear for SignalDefinitions::Vehicle_Chassis_Axle_Wheel_Brake_PadWear;
  alias Vehicle_Chassis_Axle_Wheel_Speed for SignalDefinitions::Vehicle_Chassis_Axle_Wheel_Speed;
  alias Vehicle_Chassis_Axle_Wheel_Tire_AirTemperature for SignalDefinitions::Vehicle_Chassis_Axle_Wheel_Tire_AirTemperature;
  alias Vehicle_Chassis_Axle_Wheel_Tire_IsPressureLow for SignalDefinitions::Vehicle_Chassis_Axle_Wheel_Tire_IsPressureLow;
  alias Vehicle_Chassis_Axle_Wheel_Tire_Pressure for SignalDefinitions::Vehicle_Chassis_Axle_Wheel_Tire_Pressure;
  alias Vehicle_Chassis_Axle_Wheel_Tire_RubberTemperature for SignalDefinitions::Vehicle_Chassis_Axle_Wheel_Tire_RubberTemperature;
  alias Vehicle_Chassis_Axle_Wheel_Tire_Temperature for SignalDefinitions::Vehicle_Chassis_Axle_Wheel_Tire_Temperature;
  alias Vehicle_Chassis_Axle_Wheel_Torque for SignalDefinitions::Vehicle_Chassis_Axle_Wheel_Torque;
  alias Vehicle_Chassis_Axle_WheelCount for SignalDefinitions::Vehicle_Chassis_Axle_WheelCount;
  alias Vehicle_Chassis_Axle_WheelDiameter for SignalDefinitions::Vehicle_Chassis_Axle_WheelDiameter;
  alias Vehicle_Chassis_Axle_WheelWidth for SignalDefinitions::Vehicle_Chassis_Axle_WheelWidth;
  alias Vehicle_Chassis_AxleCount for SignalDefinitions::Vehicle_Chassis_AxleCount;
  alias Vehicle_Chassis_Brake_IsDriverEmergencyBrakingDetected for SignalDefinitions::Vehicle_Chassis_Brake_IsDriverEmergencyBrakingDetected;
  alias Vehicle_Chassis_Brake_PedalPosition for SignalDefinitions::Vehicle_Chassis_Brake_PedalPosition;
  alias Vehicle_Chassis_ParkingBrake_IsAutoApplyEnabled for SignalDefinitions::Vehicle_Chassis_ParkingBrake_IsAutoApplyEnabled;
  alias Vehicle_Chassis_ParkingBrake_IsEngaged for SignalDefinitions::Vehicle_Chassis_ParkingBrake_IsEngaged;
  alias Vehicle_Chassis_SteeringWheel_Angle for SignalDefinitions::Vehicle_Chassis_SteeringWheel_Angle;
  alias Vehicle_Chassis_SteeringWheel_Extension for SignalDefinitions::Vehicle_Chassis_SteeringWheel_Extension;
  alias Vehicle_Chassis_SteeringWheel_HeatingCooling for SignalDefinitions::Vehicle_Chassis_SteeringWheel_HeatingCooling;
  alias Vehicle_Chassis_SteeringWheel_Tilt for SignalDefinitions::Vehicle_Chassis_SteeringWheel_Tilt;
  alias Vehicle_Chassis_Wheelbase for SignalDefinitions::Vehicle_Chassis_Wheelbase;
  alias Vehicle_Connectivity_IsConnectivityAvailable for SignalDefinitions::Vehicle_Connectivity_IsConnectivityAvailable;
  alias Vehicle_ControlUnit_Health_Network_CAN_IsNetworkOK for SignalDefinitions::Vehicle_ControlUnit_Health_Network_CAN_IsNetworkOK;
  alias Vehicle_ControlUnit_Health_Network_ETH_IsNetworkOK for SignalDefinitions::Vehicle_ControlUnit_Health_Network_ETH_IsNetworkOK;
  alias Vehicle_ControlUnit_Health_Resources_Power for SignalDefinitions::Vehicle_ControlUnit_Health_Resources_Power;
  alias Vehicle_ControlUnit_Health_Resources_Temperature for SignalDefinitions::Vehicle_ControlUnit_Health_Resources_Temperature;
  alias Vehicle_ControlUnit_Health_Resources_Utilization_CPU for SignalDefinitions::Vehicle_ControlUnit_Health_Resources_Utilization_CPU;
  alias Vehicle_ControlUnit_Health_Resources_Utilization_Memory for SignalDefinitions::Vehicle_ControlUnit_Health_Resources_Utilization_Memory;
  alias Vehicle_ControlUnit_Health_SWSupervision_IsAliveTriggered for SignalDefinitions::Vehicle_ControlUnit_Health_SWSupervision_IsAliveTriggered;
  alias Vehicle_ControlUnit_Health_SWSupervision_IsDeadlineTriggered for SignalDefinitions::Vehicle_ControlUnit_Health_SWSupervision_IsDeadlineTriggered;
  alias Vehicle_ControlUnit_Health_SWSupervision_IsLogicalTriggered for SignalDefinitions::Vehicle_ControlUnit_Health_SWSupervision_IsLogicalTriggered;
  alias Vehicle_ControlUnit_Health_SWSupervision_IsWatchdogTriggered for SignalDefinitions::Vehicle_ControlUnit_Health_SWSupervision_IsWatchdogTriggered;
  alias Vehicle_ControlUnit_ID for SignalDefinitions::Vehicle_ControlUnit_ID;
  alias Vehicle_CurbWeight for SignalDefinitions::Vehicle_CurbWeight;
  alias Vehicle_CurrentLocation_Altitude for SignalDefinitions::Vehicle_CurrentLocation_Altitude;
  alias Vehicle_CurrentLocation_GNSSReceiver_FixType for SignalDefinitions::Vehicle_CurrentLocation_GNSSReceiver_FixType;
  alias Vehicle_CurrentLocation_GNSSReceiver_MountingPosition_X for SignalDefinitions::Vehicle_CurrentLocation_GNSSReceiver_MountingPosition_X;
  alias Vehicle_CurrentLocation_GNSSReceiver_MountingPosition_Y for SignalDefinitions::Vehicle_CurrentLocation_GNSSReceiver_MountingPosition_Y;
  alias Vehicle_CurrentLocation_GNSSReceiver_MountingPosition_Z for SignalDefinitions::Vehicle_CurrentLocation_GNSSReceiver_MountingPosition_Z;
  alias Vehicle_CurrentLocation_Heading for SignalDefinitions::Vehicle_CurrentLocation_Heading;
  alias Vehicle_CurrentLocation_HorizontalAccuracy for SignalDefinitions::Vehicle_CurrentLocation_HorizontalAccuracy;
  alias Vehicle_CurrentLocation_Latitude for SignalDefinitions::Vehicle_CurrentLocation_Latitude;
  alias Vehicle_CurrentLocation_Longitude for SignalDefinitions::Vehicle_CurrentLocation_Longitude;
  alias Vehicle_CurrentLocation_Timestamp for SignalDefinitions::Vehicle_CurrentLocation_Timestamp;
  alias Vehicle_CurrentLocation_VerticalAccuracy for SignalDefinitions::Vehicle_CurrentLocation_VerticalAccuracy;
  alias Vehicle_CurrentOverallWeight for SignalDefinitions::Vehicle_CurrentOverallWeight;
  alias Vehicle_Diagnostics_DTCCount for SignalDefinitions::Vehicle_Diagnostics_DTCCount;
  alias Vehicle_Diagnostics_DTCList for SignalDefinitions::Vehicle_Diagnostics_DTCList;
  alias Vehicle_Driver_AttentiveProbability for SignalDefinitions::Vehicle_Driver_AttentiveProbability;
  alias Vehicle_Driver_DistractionLevel for SignalDefinitions::Vehicle_Driver_DistractionLevel;
  alias Vehicle_Driver_FatigueLevel for SignalDefinitions::Vehicle_Driver_FatigueLevel;
  alias Vehicle_Driver_HeartRate for SignalDefinitions::Vehicle_Driver_HeartRate;
  alias Vehicle_Driver_IsEyesOnRoad for SignalDefinitions::Vehicle_Driver_IsEyesOnRoad;
  alias Vehicle_Driver_IsHandsOnWheel for SignalDefinitions::Vehicle_Driver_IsHandsOnWheel;
  alias Vehicle_EmissionsCO2 for SignalDefinitions::Vehicle_EmissionsCO2;
  alias Vehicle_Exterior_AirTemperature for SignalDefinitions::Vehicle_Exterior_AirTemperature;
  alias Vehicle_Exterior_Humidity for SignalDefinitions::Vehicle_Exterior_Humidity;
  alias Vehicle_Exterior_LightIntensity for SignalDefinitions::Vehicle_Exterior_LightIntensity;
  alias Vehicle_Exterior_RoadSurfaceCondition for SignalDefinitions::Vehicle_Exterior_RoadSurfaceCondition;
  alias Vehicle_GrossWeight for SignalDefinitions::Vehicle_GrossWeight;
  alias Vehicle_Height for SignalDefinitions::Vehicle_Height;
  alias Vehicle_IsAutoPowerOptimize for SignalDefinitions::Vehicle_IsAutoPowerOptimize;
  alias Vehicle_IsBrokenDown for SignalDefinitions::Vehicle_IsBrokenDown;
  alias Vehicle_IsMoving for SignalDefinitions::Vehicle_IsMoving;
  alias Vehicle_Length for SignalDefinitions::Vehicle_Length;
  alias Vehicle_LowVoltageBattery_CurrentCurrent for SignalDefinitions::Vehicle_LowVoltageBattery_CurrentCurrent;
  alias Vehicle_LowVoltageBattery_CurrentVoltage for SignalDefinitions::Vehicle_LowVoltageBattery_CurrentVoltage;
  alias Vehicle_LowVoltageBattery_NominalCapacity for SignalDefinitions::Vehicle_LowVoltageBattery_NominalCapacity;
  alias Vehicle_LowVoltageBattery_NominalVoltage for SignalDefinitions::Vehicle_LowVoltageBattery_NominalVoltage;
  alias Vehicle_LowVoltageSystemState for SignalDefinitions::Vehicle_LowVoltageSystemState;
  alias Vehicle_MaxTowBallWeight for SignalDefinitions::Vehicle_MaxTowBallWeight;
  alias Vehicle_MaxTowWeight for SignalDefinitions::Vehicle_MaxTowWeight;
  alias Vehicle_MotionManagement_Brake_Axle_TorqueDistributionFrictionRightMaximum for SignalDefinitions::Vehicle_MotionManagement_Brake_Axle_TorqueDistributionFrictionRightMaximum;
  alias Vehicle_MotionManagement_Brake_Axle_TorqueDistributionFrictionRightMinimum for SignalDefinitions::Vehicle_MotionManagement_Brake_Axle_TorqueDistributionFrictionRightMinimum;
  alias Vehicle_MotionManagement_Brake_Axle_TorqueElectricMinimum for SignalDefinitions::Vehicle_MotionManagement_Brake_Axle_TorqueElectricMinimum;
  alias Vehicle_MotionManagement_Brake_Axle_TorqueFrictionDifferenceMaximum for SignalDefinitions::Vehicle_MotionManagement_Brake_Axle_TorqueFrictionDifferenceMaximum;
  alias Vehicle_MotionManagement_Brake_Axle_Wheel_OmegaLower for SignalDefinitions::Vehicle_MotionManagement_Brake_Axle_Wheel_OmegaLower;
  alias Vehicle_MotionManagement_Brake_Axle_Wheel_OmegaUpper for SignalDefinitions::Vehicle_MotionManagement_Brake_Axle_Wheel_OmegaUpper;
  alias Vehicle_MotionManagement_Brake_Axle_Wheel_Torque for SignalDefinitions::Vehicle_MotionManagement_Brake_Axle_Wheel_Torque;
  alias Vehicle_MotionManagement_Brake_Axle_Wheel_TorqueArbitrated for SignalDefinitions::Vehicle_MotionManagement_Brake_Axle_Wheel_TorqueArbitrated;
  alias Vehicle_MotionManagement_Brake_Axle_Wheel_TorqueFrictionMaximum for SignalDefinitions::Vehicle_MotionManagement_Brake_Axle_Wheel_TorqueFrictionMaximum;
  alias Vehicle_MotionManagement_Brake_Axle_Wheel_TorqueFrictionMinimum for SignalDefinitions::Vehicle_MotionManagement_Brake_Axle_Wheel_TorqueFrictionMinimum;
  alias Vehicle_MotionManagement_Brake_VehicleForceDistributionFrontMaximum for SignalDefinitions::Vehicle_MotionManagement_Brake_VehicleForceDistributionFrontMaximum;
  alias Vehicle_MotionManagement_Brake_VehicleForceDistributionFrontMinimum for SignalDefinitions::Vehicle_MotionManagement_Brake_VehicleForceDistributionFrontMinimum;
  alias Vehicle_MotionManagement_Brake_VehicleForceElectric for SignalDefinitions::Vehicle_MotionManagement_Brake_VehicleForceElectric;
  alias Vehicle_MotionManagement_Brake_VehicleForceElectricMinimumArbitrated for SignalDefinitions::Vehicle_MotionManagement_Brake_VehicleForceElectricMinimumArbitrated;
  alias Vehicle_MotionManagement_Brake_VehicleForceMaximum for SignalDefinitions::Vehicle_MotionManagement_Brake_VehicleForceMaximum;
  alias Vehicle_MotionManagement_ElectricAxle_RotationalSpeed for SignalDefinitions::Vehicle_MotionManagement_ElectricAxle_RotationalSpeed;
  alias Vehicle_MotionManagement_ElectricAxle_RotationalSpeedMaximumLimit for SignalDefinitions::Vehicle_MotionManagement_ElectricAxle_RotationalSpeedMaximumLimit;
  alias Vehicle_MotionManagement_ElectricAxle_RotationalSpeedMinimumLimit for SignalDefinitions::Vehicle_MotionManagement_ElectricAxle_RotationalSpeedMinimumLimit;
  alias Vehicle_MotionManagement_ElectricAxle_RotationalSpeedTarget for SignalDefinitions::Vehicle_MotionManagement_ElectricAxle_RotationalSpeedTarget;
  alias Vehicle_MotionManagement_ElectricAxle_Torque for SignalDefinitions::Vehicle_MotionManagement_ElectricAxle_Torque;
  alias Vehicle_MotionManagement_ElectricAxle_TorqueMaximum for SignalDefinitions::Vehicle_MotionManagement_ElectricAxle_TorqueMaximum;
  alias Vehicle_MotionManagement_ElectricAxle_TorqueMaximumLimit for SignalDefinitions::Vehicle_MotionManagement_ElectricAxle_TorqueMaximumLimit;
  alias Vehicle_MotionManagement_ElectricAxle_TorqueMinimum for SignalDefinitions::Vehicle_MotionManagement_ElectricAxle_TorqueMinimum;
  alias Vehicle_MotionManagement_ElectricAxle_TorqueMinimumLimit for SignalDefinitions::Vehicle_MotionManagement_ElectricAxle_TorqueMinimumLimit;
  alias Vehicle_MotionManagement_ElectricAxle_TorqueTarget for SignalDefinitions::Vehicle_MotionManagement_ElectricAxle_TorqueTarget;
  alias Vehicle_MotionManagement_Steering_Axle_Row1_PositionOffsetTargetMode for SignalDefinitions::Vehicle_MotionManagement_Steering_Axle_Row1_PositionOffsetTargetMode;
  alias Vehicle_MotionManagement_Steering_Axle_Row1_PositionTargetMode for SignalDefinitions::Vehicle_MotionManagement_Steering_Axle_Row1_PositionTargetMode;
  alias Vehicle_MotionManagement_Steering_Axle_Row1_RackPosition for SignalDefinitions::Vehicle_MotionManagement_Steering_Axle_Row1_RackPosition;
  alias Vehicle_MotionManagement_Steering_Axle_Row1_RackPositionOffsetTarget for SignalDefinitions::Vehicle_MotionManagement_Steering_Axle_Row1_RackPositionOffsetTarget;
  alias Vehicle_MotionManagement_Steering_Axle_Row1_RackPositionTarget for SignalDefinitions::Vehicle_MotionManagement_Steering_Axle_Row1_RackPositionTarget;
  alias Vehicle_MotionManagement_Steering_Axle_Row1_SteerAngle for SignalDefinitions::Vehicle_MotionManagement_Steering_Axle_Row1_SteerAngle;
  alias Vehicle_MotionManagement_Steering_Axle_Row1_SteerAngleOffsetTarget for SignalDefinitions::Vehicle_MotionManagement_Steering_Axle_Row1_SteerAngleOffsetTarget;
  alias Vehicle_MotionManagement_Steering_Axle_Row1_SteerAngleTarget for SignalDefinitions::Vehicle_MotionManagement_Steering_Axle_Row1_SteerAngleTarget;
  alias Vehicle_MotionManagement_Steering_Axle_Row2_SteerAngle for SignalDefinitions::Vehicle_MotionManagement_Steering_Axle_Row2_SteerAngle;
  alias Vehicle_MotionManagement_Steering_Axle_Row2_SteerAngleTarget for SignalDefinitions::Vehicle_MotionManagement_Steering_Axle_Row2_SteerAngleTarget;
  alias Vehicle_MotionManagement_Steering_Axle_Row2_SteerAngleVelocityTarget for SignalDefinitions::Vehicle_MotionManagement_Steering_Axle_Row2_SteerAngleVelocityTarget;
  alias Vehicle_MotionManagement_Steering_SteeringWheel_Angle for SignalDefinitions::Vehicle_MotionManagement_Steering_SteeringWheel_Angle;
  alias Vehicle_MotionManagement_Steering_SteeringWheel_AngleTarget for SignalDefinitions::Vehicle_MotionManagement_Steering_SteeringWheel_AngleTarget;
  alias Vehicle_MotionManagement_Steering_SteeringWheel_AngleTargetMode for SignalDefinitions::Vehicle_MotionManagement_Steering_SteeringWheel_AngleTargetMode;
  alias Vehicle_MotionManagement_Steering_SteeringWheel_Torque for SignalDefinitions::Vehicle_MotionManagement_Steering_SteeringWheel_Torque;
  alias Vehicle_MotionManagement_Steering_SteeringWheel_TorqueOffsetTarget for SignalDefinitions::Vehicle_MotionManagement_Steering_SteeringWheel_TorqueOffsetTarget;
  alias Vehicle_MotionManagement_Steering_SteeringWheel_TorqueOffsetTargetMode for SignalDefinitions::Vehicle_MotionManagement_Steering_SteeringWheel_TorqueOffsetTargetMode;
  alias Vehicle_MotionManagement_Steering_SteeringWheel_TorqueTarget for SignalDefinitions::Vehicle_MotionManagement_Steering_SteeringWheel_TorqueTarget;
  alias Vehicle_MotionManagement_Steering_SteeringWheel_TorqueTargetMode for SignalDefinitions::Vehicle_MotionManagement_Steering_SteeringWheel_TorqueTargetMode;
  alias Vehicle_MotionManagement_Suspension_Axle_RollTorque for SignalDefinitions::Vehicle_MotionManagement_Suspension_Axle_RollTorque;
  alias Vehicle_MotionManagement_Suspension_Axle_Wheel_DampingForce for SignalDefinitions::Vehicle_MotionManagement_Suspension_Axle_Wheel_DampingForce;
  alias Vehicle_MotionManagement_Suspension_Axle_Wheel_DampingForceTarget for SignalDefinitions::Vehicle_MotionManagement_Suspension_Axle_Wheel_DampingForceTarget;
  alias Vehicle_MotionManagement_Suspension_Axle_Wheel_DampingRate for SignalDefinitions::Vehicle_MotionManagement_Suspension_Axle_Wheel_DampingRate;
  alias Vehicle_MotionManagement_Suspension_Axle_Wheel_DampingRateTarget for SignalDefinitions::Vehicle_MotionManagement_Suspension_Axle_Wheel_DampingRateTarget;
  alias Vehicle_MotionManagement_Suspension_DampingPrioTarget for SignalDefinitions::Vehicle_MotionManagement_Suspension_DampingPrioTarget;
  alias Vehicle_MotionManagement_Suspension_RollPrioTarget for SignalDefinitions::Vehicle_MotionManagement_Suspension_RollPrioTarget;
  alias Vehicle_MotionManagement_Suspension_RollTorqueDistributionFrontMaximum for SignalDefinitions::Vehicle_MotionManagement_Suspension_RollTorqueDistributionFrontMaximum;
  alias Vehicle_MotionManagement_Suspension_RollTorqueDistributionFrontMinimum for SignalDefinitions::Vehicle_MotionManagement_Suspension_RollTorqueDistributionFrontMinimum;
  alias Vehicle_MotionManagement_Suspension_RollTorqueTarget for SignalDefinitions::Vehicle_MotionManagement_Suspension_RollTorqueTarget;
  alias Vehicle_Occupant_HeadPosition_Pitch for SignalDefinitions::Vehicle_Occupant_HeadPosition_Pitch;
  alias Vehicle_Occupant_HeadPosition_Roll for SignalDefinitions::Vehicle_Occupant_HeadPosition_Roll;
  alias Vehicle_Occupant_HeadPosition_X for SignalDefinitions::Vehicle_Occupant_HeadPosition_X;
  alias Vehicle_Occupant_HeadPosition_Y for SignalDefinitions::Vehicle_Occupant_HeadPosition_Y;
  alias Vehicle_Occupant_HeadPosition_Yaw for SignalDefinitions::Vehicle_Occupant_HeadPosition_Yaw;
  alias Vehicle_Occupant_HeadPosition_Z for SignalDefinitions::Vehicle_Occupant_HeadPosition_Z;
  alias Vehicle_Occupant_Identifier_Issuer for SignalDefinitions::Vehicle_Occupant_Identifier_Issuer;
  alias Vehicle_Occupant_Identifier_Subject for SignalDefinitions::Vehicle_Occupant_Identifier_Subject;
  alias Vehicle_Occupant_MidEyeGaze_Azimuth for SignalDefinitions::Vehicle_Occupant_MidEyeGaze_Azimuth;
  alias Vehicle_Occupant_MidEyeGaze_Elevation for SignalDefinitions::Vehicle_Occupant_MidEyeGaze_Elevation;
  alias Vehicle_Orientation_Pitch for SignalDefinitions::Vehicle_Orientation_Pitch;
  alias Vehicle_Orientation_Roll for SignalDefinitions::Vehicle_Orientation_Roll;
  alias Vehicle_Orientation_Yaw for SignalDefinitions::Vehicle_Orientation_Yaw;
  alias Vehicle_PowerOptimizeLevel for SignalDefinitions::Vehicle_PowerOptimizeLevel;
  alias Vehicle_Powertrain_AccumulatedBrakingEnergy for SignalDefinitions::Vehicle_Powertrain_AccumulatedBrakingEnergy;
  alias Vehicle_Powertrain_CombustionEngine_AspirationType for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_AspirationType;
  alias Vehicle_Powertrain_CombustionEngine_Bore for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_Bore;
  alias Vehicle_Powertrain_CombustionEngine_CompressionRatio for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_CompressionRatio;
  alias Vehicle_Powertrain_CombustionEngine_Configuration for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_Configuration;
  alias Vehicle_Powertrain_CombustionEngine_DieselExhaustFluid_Capacity for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_DieselExhaustFluid_Capacity;
  alias Vehicle_Powertrain_CombustionEngine_DieselExhaustFluid_IsLevelLow for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_DieselExhaustFluid_IsLevelLow;
  alias Vehicle_Powertrain_CombustionEngine_DieselExhaustFluid_Level for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_DieselExhaustFluid_Level;
  alias Vehicle_Powertrain_CombustionEngine_DieselExhaustFluid_Range for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_DieselExhaustFluid_Range;
  alias Vehicle_Powertrain_CombustionEngine_DieselParticulateFilter_DeltaPressure for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_DieselParticulateFilter_DeltaPressure;
  alias Vehicle_Powertrain_CombustionEngine_DieselParticulateFilter_InletTemperature for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_DieselParticulateFilter_InletTemperature;
  alias Vehicle_Powertrain_CombustionEngine_DieselParticulateFilter_OutletTemperature for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_DieselParticulateFilter_OutletTemperature;
  alias Vehicle_Powertrain_CombustionEngine_Displacement for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_Displacement;
  alias Vehicle_Powertrain_CombustionEngine_EOP for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_EOP;
  alias Vehicle_Powertrain_CombustionEngine_EngineCode for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_EngineCode;
  alias Vehicle_Powertrain_CombustionEngine_EngineCoolant_Capacity for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_EngineCoolant_Capacity;
  alias Vehicle_Powertrain_CombustionEngine_EngineCoolant_Level for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_EngineCoolant_Level;
  alias Vehicle_Powertrain_CombustionEngine_EngineCoolant_LifeRemaining for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_EngineCoolant_LifeRemaining;
  alias Vehicle_Powertrain_CombustionEngine_EngineCoolant_Temperature for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_EngineCoolant_Temperature;
  alias Vehicle_Powertrain_CombustionEngine_EngineHours for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_EngineHours;
  alias Vehicle_Powertrain_CombustionEngine_EngineOil_Capacity for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_EngineOil_Capacity;
  alias Vehicle_Powertrain_CombustionEngine_EngineOil_Level for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_EngineOil_Level;
  alias Vehicle_Powertrain_CombustionEngine_EngineOil_LifeRemaining for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_EngineOil_LifeRemaining;
  alias Vehicle_Powertrain_CombustionEngine_EngineOil_PressureStatus for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_EngineOil_PressureStatus;
  alias Vehicle_Powertrain_CombustionEngine_EngineOil_Temperature for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_EngineOil_Temperature;
  alias Vehicle_Powertrain_CombustionEngine_IdleHours for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_IdleHours;
  alias Vehicle_Powertrain_CombustionEngine_IsRunning for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_IsRunning;
  alias Vehicle_Powertrain_CombustionEngine_MAF for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_MAF;
  alias Vehicle_Powertrain_CombustionEngine_MAP for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_MAP;
  alias Vehicle_Powertrain_CombustionEngine_MaxPower for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_MaxPower;
  alias Vehicle_Powertrain_CombustionEngine_MaxTorque for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_MaxTorque;
  alias Vehicle_Powertrain_CombustionEngine_NumberOfCylinders for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_NumberOfCylinders;
  alias Vehicle_Powertrain_CombustionEngine_NumberOfValvesPerCylinder for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_NumberOfValvesPerCylinder;
  alias Vehicle_Powertrain_CombustionEngine_Power for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_Power;
  alias Vehicle_Powertrain_CombustionEngine_Speed for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_Speed;
  alias Vehicle_Powertrain_CombustionEngine_StrokeLength for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_StrokeLength;
  alias Vehicle_Powertrain_CombustionEngine_TPS for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_TPS;
  alias Vehicle_Powertrain_CombustionEngine_Torque for SignalDefinitions::Vehicle_Powertrain_CombustionEngine_Torque;
  alias Vehicle_Powertrain_ElectricMotor_EngineCode for SignalDefinitions::Vehicle_Powertrain_ElectricMotor_EngineCode;
  alias Vehicle_Powertrain_ElectricMotor_EngineCoolant_Capacity for SignalDefinitions::Vehicle_Powertrain_ElectricMotor_EngineCoolant_Capacity;
  alias Vehicle_Powertrain_ElectricMotor_EngineCoolant_Level for SignalDefinitions::Vehicle_Powertrain_ElectricMotor_EngineCoolant_Level;
  alias Vehicle_Powertrain_ElectricMotor_EngineCoolant_LifeRemaining for SignalDefinitions::Vehicle_Powertrain_ElectricMotor_EngineCoolant_LifeRemaining;
  alias Vehicle_Powertrain_ElectricMotor_EngineCoolant_Temperature for SignalDefinitions::Vehicle_Powertrain_ElectricMotor_EngineCoolant_Temperature;
  alias Vehicle_Powertrain_ElectricMotor_MaxPower for SignalDefinitions::Vehicle_Powertrain_ElectricMotor_MaxPower;
  alias Vehicle_Powertrain_ElectricMotor_MaxRegenPower for SignalDefinitions::Vehicle_Powertrain_ElectricMotor_MaxRegenPower;
  alias Vehicle_Powertrain_ElectricMotor_MaxRegenTorque for SignalDefinitions::Vehicle_Powertrain_ElectricMotor_MaxRegenTorque;
  alias Vehicle_Powertrain_ElectricMotor_MaxTorque for SignalDefinitions::Vehicle_Powertrain_ElectricMotor_MaxTorque;
  alias Vehicle_Powertrain_ElectricMotor_Power for SignalDefinitions::Vehicle_Powertrain_ElectricMotor_Power;
  alias Vehicle_Powertrain_ElectricMotor_Speed for SignalDefinitions::Vehicle_Powertrain_ElectricMotor_Speed;
  alias Vehicle_Powertrain_ElectricMotor_Temperature for SignalDefinitions::Vehicle_Powertrain_ElectricMotor_Temperature;
  alias Vehicle_Powertrain_ElectricMotor_TimeInUse for SignalDefinitions::Vehicle_Powertrain_ElectricMotor_TimeInUse;
  alias Vehicle_Powertrain_ElectricMotor_Torque for SignalDefinitions::Vehicle_Powertrain_ElectricMotor_Torque;
  alias Vehicle_Powertrain_FuelSystem_AbsoluteLevel for SignalDefinitions::Vehicle_Powertrain_FuelSystem_AbsoluteLevel;
  alias Vehicle_Powertrain_FuelSystem_AfterRefuelingFuelEconomy for SignalDefinitions::Vehicle_Powertrain_FuelSystem_AfterRefuelingFuelEconomy;
  alias Vehicle_Powertrain_FuelSystem_AverageConsumption for SignalDefinitions::Vehicle_Powertrain_FuelSystem_AverageConsumption;
  alias Vehicle_Powertrain_FuelSystem_ConsumptionSinceLastRefuel for SignalDefinitions::Vehicle_Powertrain_FuelSystem_ConsumptionSinceLastRefuel;
  alias Vehicle_Powertrain_FuelSystem_ConsumptionSinceStart for SignalDefinitions::Vehicle_Powertrain_FuelSystem_ConsumptionSinceStart;
  alias Vehicle_Powertrain_FuelSystem_CumulativeFuelEconomy for SignalDefinitions::Vehicle_Powertrain_FuelSystem_CumulativeFuelEconomy;
  alias Vehicle_Powertrain_FuelSystem_DriveFuelEconomy for SignalDefinitions::Vehicle_Powertrain_FuelSystem_DriveFuelEconomy;
  alias Vehicle_Powertrain_FuelSystem_HybridType for SignalDefinitions::Vehicle_Powertrain_FuelSystem_HybridType;
  alias Vehicle_Powertrain_FuelSystem_InstantConsumption for SignalDefinitions::Vehicle_Powertrain_FuelSystem_InstantConsumption;
  alias Vehicle_Powertrain_FuelSystem_InstantantFuelEconomy for SignalDefinitions::Vehicle_Powertrain_FuelSystem_InstantantFuelEconomy;
  alias Vehicle_Powertrain_FuelSystem_IsEngineStopStartEnabled for SignalDefinitions::Vehicle_Powertrain_FuelSystem_IsEngineStopStartEnabled;
  alias Vehicle_Powertrain_FuelSystem_IsFuelLevelEmpty for SignalDefinitions::Vehicle_Powertrain_FuelSystem_IsFuelLevelEmpty;
  alias Vehicle_Powertrain_FuelSystem_IsFuelLevelLow for SignalDefinitions::Vehicle_Powertrain_FuelSystem_IsFuelLevelLow;
  alias Vehicle_Powertrain_FuelSystem_IsFuelPortFlapOpen for SignalDefinitions::Vehicle_Powertrain_FuelSystem_IsFuelPortFlapOpen;
  alias Vehicle_Powertrain_FuelSystem_Range for SignalDefinitions::Vehicle_Powertrain_FuelSystem_Range;
  alias Vehicle_Powertrain_FuelSystem_RefuelPortPosition for SignalDefinitions::Vehicle_Powertrain_FuelSystem_RefuelPortPosition;
  alias Vehicle_Powertrain_FuelSystem_RelativeLevel for SignalDefinitions::Vehicle_Powertrain_FuelSystem_RelativeLevel;
  alias Vehicle_Powertrain_FuelSystem_SupportedFuel for SignalDefinitions::Vehicle_Powertrain_FuelSystem_SupportedFuel;
  alias Vehicle_Powertrain_FuelSystem_SupportedFuelTypes for SignalDefinitions::Vehicle_Powertrain_FuelSystem_SupportedFuelTypes;
  alias Vehicle_Powertrain_FuelSystem_TankCapacity for SignalDefinitions::Vehicle_Powertrain_FuelSystem_TankCapacity;
  alias Vehicle_Powertrain_FuelSystem_TimeRemaining for SignalDefinitions::Vehicle_Powertrain_FuelSystem_TimeRemaining;
  alias Vehicle_Powertrain_IsAutoPowerOptimize for SignalDefinitions::Vehicle_Powertrain_IsAutoPowerOptimize;
  alias Vehicle_Powertrain_PowerOptimizeLevel for SignalDefinitions::Vehicle_Powertrain_PowerOptimizeLevel;
  alias Vehicle_Powertrain_Range for SignalDefinitions::Vehicle_Powertrain_Range;
  alias Vehicle_Powertrain_RangeExtender_ChargeDepleting_EnergyConsumption for SignalDefinitions::Vehicle_Powertrain_RangeExtender_ChargeDepleting_EnergyConsumption;
  alias Vehicle_Powertrain_RangeExtender_ChargeDepleting_Range for SignalDefinitions::Vehicle_Powertrain_RangeExtender_ChargeDepleting_Range;
  alias Vehicle_Powertrain_RangeExtender_ChargeSustaining_FuelEconomy for SignalDefinitions::Vehicle_Powertrain_RangeExtender_ChargeSustaining_FuelEconomy;
  alias Vehicle_Powertrain_RangeExtender_ChargeSustaining_Range for SignalDefinitions::Vehicle_Powertrain_RangeExtender_ChargeSustaining_Range;
  alias Vehicle_Powertrain_RangeExtender_CombinedFuelEconomy for SignalDefinitions::Vehicle_Powertrain_RangeExtender_CombinedFuelEconomy;
  alias Vehicle_Powertrain_RangeExtender_OperatingMode for SignalDefinitions::Vehicle_Powertrain_RangeExtender_OperatingMode;
  alias Vehicle_Powertrain_TimeRemaining for SignalDefinitions::Vehicle_Powertrain_TimeRemaining;
  alias Vehicle_Powertrain_TractionBattery_AccumulatedChargedEnergy for SignalDefinitions::Vehicle_Powertrain_TractionBattery_AccumulatedChargedEnergy;
  alias Vehicle_Powertrain_TractionBattery_AccumulatedChargedThroughput for SignalDefinitions::Vehicle_Powertrain_TractionBattery_AccumulatedChargedThroughput;
  alias Vehicle_Powertrain_TractionBattery_AccumulatedConsumedEnergy for SignalDefinitions::Vehicle_Powertrain_TractionBattery_AccumulatedConsumedEnergy;
  alias Vehicle_Powertrain_TractionBattery_AccumulatedConsumedThroughput for SignalDefinitions::Vehicle_Powertrain_TractionBattery_AccumulatedConsumedThroughput;
  alias Vehicle_Powertrain_TractionBattery_BatteryConditioning_IsActive for SignalDefinitions::Vehicle_Powertrain_TractionBattery_BatteryConditioning_IsActive;
  alias Vehicle_Powertrain_TractionBattery_BatteryConditioning_IsOngoing for SignalDefinitions::Vehicle_Powertrain_TractionBattery_BatteryConditioning_IsOngoing;
  alias Vehicle_Powertrain_TractionBattery_BatteryConditioning_RequestedMode for SignalDefinitions::Vehicle_Powertrain_TractionBattery_BatteryConditioning_RequestedMode;
  alias Vehicle_Powertrain_TractionBattery_BatteryConditioning_StartTime for SignalDefinitions::Vehicle_Powertrain_TractionBattery_BatteryConditioning_StartTime;
  alias Vehicle_Powertrain_TractionBattery_BatteryConditioning_TargetTemperature for SignalDefinitions::Vehicle_Powertrain_TractionBattery_BatteryConditioning_TargetTemperature;
  alias Vehicle_Powertrain_TractionBattery_BatteryConditioning_TargetTime for SignalDefinitions::Vehicle_Powertrain_TractionBattery_BatteryConditioning_TargetTime;
  alias Vehicle_Powertrain_TractionBattery_CellVoltage_CellVoltages for SignalDefinitions::Vehicle_Powertrain_TractionBattery_CellVoltage_CellVoltages;
  alias Vehicle_Powertrain_TractionBattery_CellVoltage_IdMax for SignalDefinitions::Vehicle_Powertrain_TractionBattery_CellVoltage_IdMax;
  alias Vehicle_Powertrain_TractionBattery_CellVoltage_IdMin for SignalDefinitions::Vehicle_Powertrain_TractionBattery_CellVoltage_IdMin;
  alias Vehicle_Powertrain_TractionBattery_CellVoltage_Max for SignalDefinitions::Vehicle_Powertrain_TractionBattery_CellVoltage_Max;
  alias Vehicle_Powertrain_TractionBattery_CellVoltage_Min for SignalDefinitions::Vehicle_Powertrain_TractionBattery_CellVoltage_Min;
  alias Vehicle_Powertrain_TractionBattery_Charging_AveragePower for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_AveragePower;
  alias Vehicle_Powertrain_TractionBattery_Charging_ChargeCurrent_DC for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_ChargeCurrent_DC;
  alias Vehicle_Powertrain_TractionBattery_Charging_ChargeCurrent_Phase1 for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_ChargeCurrent_Phase1;
  alias Vehicle_Powertrain_TractionBattery_Charging_ChargeCurrent_Phase2 for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_ChargeCurrent_Phase2;
  alias Vehicle_Powertrain_TractionBattery_Charging_ChargeCurrent_Phase3 for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_ChargeCurrent_Phase3;
  alias Vehicle_Powertrain_TractionBattery_Charging_ChargeLimit for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_ChargeLimit;
  alias Vehicle_Powertrain_TractionBattery_Charging_ChargeRate for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_ChargeRate;
  alias Vehicle_Powertrain_TractionBattery_Charging_ChargeVoltage_DC for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_ChargeVoltage_DC;
  alias Vehicle_Powertrain_TractionBattery_Charging_ChargeVoltage_Phase1 for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_ChargeVoltage_Phase1;
  alias Vehicle_Powertrain_TractionBattery_Charging_ChargeVoltage_Phase2 for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_ChargeVoltage_Phase2;
  alias Vehicle_Powertrain_TractionBattery_Charging_ChargeVoltage_Phase3 for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_ChargeVoltage_Phase3;
  alias Vehicle_Powertrain_TractionBattery_Charging_ChargingPort_IsChargingCableConnected for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_ChargingPort_IsChargingCableConnected;
  alias Vehicle_Powertrain_TractionBattery_Charging_ChargingPort_IsChargingCableLocked for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_ChargingPort_IsChargingCableLocked;
  alias Vehicle_Powertrain_TractionBattery_Charging_ChargingPort_IsFlapOpen for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_ChargingPort_IsFlapOpen;
  alias Vehicle_Powertrain_TractionBattery_Charging_ChargingPort_SupportedInletTypes for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_ChargingPort_SupportedInletTypes;
  alias Vehicle_Powertrain_TractionBattery_Charging_EvseId for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_EvseId;
  alias Vehicle_Powertrain_TractionBattery_Charging_IsCharging for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_IsCharging;
  alias Vehicle_Powertrain_TractionBattery_Charging_IsDischarging for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_IsDischarging;
  alias Vehicle_Powertrain_TractionBattery_Charging_Location_Altitude for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_Location_Altitude;
  alias Vehicle_Powertrain_TractionBattery_Charging_Location_Latitude for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_Location_Latitude;
  alias Vehicle_Powertrain_TractionBattery_Charging_Location_Longitude for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_Location_Longitude;
  alias Vehicle_Powertrain_TractionBattery_Charging_MaxPower for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_MaxPower;
  alias Vehicle_Powertrain_TractionBattery_Charging_MaximumChargingCurrent_DC for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_MaximumChargingCurrent_DC;
  alias Vehicle_Powertrain_TractionBattery_Charging_MaximumChargingCurrent_Phase1 for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_MaximumChargingCurrent_Phase1;
  alias Vehicle_Powertrain_TractionBattery_Charging_MaximumChargingCurrent_Phase2 for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_MaximumChargingCurrent_Phase2;
  alias Vehicle_Powertrain_TractionBattery_Charging_MaximumChargingCurrent_Phase3 for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_MaximumChargingCurrent_Phase3;
  alias Vehicle_Powertrain_TractionBattery_Charging_PowerLoss for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_PowerLoss;
  alias Vehicle_Powertrain_TractionBattery_Charging_StartStopCharging for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_StartStopCharging;
  alias Vehicle_Powertrain_TractionBattery_Charging_Temperature for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_Temperature;
  alias Vehicle_Powertrain_TractionBattery_Charging_TimeToComplete for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_TimeToComplete;
  alias Vehicle_Powertrain_TractionBattery_Charging_Timer_Mode for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_Timer_Mode;
  alias Vehicle_Powertrain_TractionBattery_Charging_Timer_Time for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Charging_Timer_Time;
  alias Vehicle_Powertrain_TractionBattery_CurrentCurrent for SignalDefinitions::Vehicle_Powertrain_TractionBattery_CurrentCurrent;
  alias Vehicle_Powertrain_TractionBattery_CurrentPower for SignalDefinitions::Vehicle_Powertrain_TractionBattery_CurrentPower;
  alias Vehicle_Powertrain_TractionBattery_CurrentVoltage for SignalDefinitions::Vehicle_Powertrain_TractionBattery_CurrentVoltage;
  alias Vehicle_Powertrain_TractionBattery_DCDC_PowerLoss for SignalDefinitions::Vehicle_Powertrain_TractionBattery_DCDC_PowerLoss;
  alias Vehicle_Powertrain_TractionBattery_DCDC_Temperature for SignalDefinitions::Vehicle_Powertrain_TractionBattery_DCDC_Temperature;
  alias Vehicle_Powertrain_TractionBattery_ErrorCodes for SignalDefinitions::Vehicle_Powertrain_TractionBattery_ErrorCodes;
  alias Vehicle_Powertrain_TractionBattery_GrossCapacity for SignalDefinitions::Vehicle_Powertrain_TractionBattery_GrossCapacity;
  alias Vehicle_Powertrain_TractionBattery_Id for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Id;
  alias Vehicle_Powertrain_TractionBattery_IsGroundConnected for SignalDefinitions::Vehicle_Powertrain_TractionBattery_IsGroundConnected;
  alias Vehicle_Powertrain_TractionBattery_IsPowerConnected for SignalDefinitions::Vehicle_Powertrain_TractionBattery_IsPowerConnected;
  alias Vehicle_Powertrain_TractionBattery_MaxVoltage for SignalDefinitions::Vehicle_Powertrain_TractionBattery_MaxVoltage;
  alias Vehicle_Powertrain_TractionBattery_NetCapacity for SignalDefinitions::Vehicle_Powertrain_TractionBattery_NetCapacity;
  alias Vehicle_Powertrain_TractionBattery_NominalVoltage for SignalDefinitions::Vehicle_Powertrain_TractionBattery_NominalVoltage;
  alias Vehicle_Powertrain_TractionBattery_PowerLoss for SignalDefinitions::Vehicle_Powertrain_TractionBattery_PowerLoss;
  alias Vehicle_Powertrain_TractionBattery_ProductionDate for SignalDefinitions::Vehicle_Powertrain_TractionBattery_ProductionDate;
  alias Vehicle_Powertrain_TractionBattery_Range for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Range;
  alias Vehicle_Powertrain_TractionBattery_StateOfCharge_Current for SignalDefinitions::Vehicle_Powertrain_TractionBattery_StateOfCharge_Current;
  alias Vehicle_Powertrain_TractionBattery_StateOfCharge_CurrentEnergy for SignalDefinitions::Vehicle_Powertrain_TractionBattery_StateOfCharge_CurrentEnergy;
  alias Vehicle_Powertrain_TractionBattery_StateOfCharge_Displayed for SignalDefinitions::Vehicle_Powertrain_TractionBattery_StateOfCharge_Displayed;
  alias Vehicle_Powertrain_TractionBattery_StateOfHealth for SignalDefinitions::Vehicle_Powertrain_TractionBattery_StateOfHealth;
  alias Vehicle_Powertrain_TractionBattery_Temperature_Average for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Temperature_Average;
  alias Vehicle_Powertrain_TractionBattery_Temperature_CellTemperature for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Temperature_CellTemperature;
  alias Vehicle_Powertrain_TractionBattery_Temperature_Max for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Temperature_Max;
  alias Vehicle_Powertrain_TractionBattery_Temperature_Min for SignalDefinitions::Vehicle_Powertrain_TractionBattery_Temperature_Min;
  alias Vehicle_Powertrain_TractionBattery_TimeRemaining for SignalDefinitions::Vehicle_Powertrain_TractionBattery_TimeRemaining;
  alias Vehicle_Powertrain_Transmission_ClutchEngagement for SignalDefinitions::Vehicle_Powertrain_Transmission_ClutchEngagement;
  alias Vehicle_Powertrain_Transmission_ClutchWear for SignalDefinitions::Vehicle_Powertrain_Transmission_ClutchWear;
  alias Vehicle_Powertrain_Transmission_CurrentGear for SignalDefinitions::Vehicle_Powertrain_Transmission_CurrentGear;
  alias Vehicle_Powertrain_Transmission_DiffLockFrontEngagement for SignalDefinitions::Vehicle_Powertrain_Transmission_DiffLockFrontEngagement;
  alias Vehicle_Powertrain_Transmission_DiffLockRearEngagement for SignalDefinitions::Vehicle_Powertrain_Transmission_DiffLockRearEngagement;
  alias Vehicle_Powertrain_Transmission_DriveType for SignalDefinitions::Vehicle_Powertrain_Transmission_DriveType;
  alias Vehicle_Powertrain_Transmission_GearChangeMode for SignalDefinitions::Vehicle_Powertrain_Transmission_GearChangeMode;
  alias Vehicle_Powertrain_Transmission_GearCount for SignalDefinitions::Vehicle_Powertrain_Transmission_GearCount;
  alias Vehicle_Powertrain_Transmission_IsElectricalPowertrainEngaged for SignalDefinitions::Vehicle_Powertrain_Transmission_IsElectricalPowertrainEngaged;
  alias Vehicle_Powertrain_Transmission_IsLowRangeEngaged for SignalDefinitions::Vehicle_Powertrain_Transmission_IsLowRangeEngaged;
  alias Vehicle_Powertrain_Transmission_IsParkLockEngaged for SignalDefinitions::Vehicle_Powertrain_Transmission_IsParkLockEngaged;
  alias Vehicle_Powertrain_Transmission_PerformanceMode for SignalDefinitions::Vehicle_Powertrain_Transmission_PerformanceMode;
  alias Vehicle_Powertrain_Transmission_SelectedGear for SignalDefinitions::Vehicle_Powertrain_Transmission_SelectedGear;
  alias Vehicle_Powertrain_Transmission_Temperature for SignalDefinitions::Vehicle_Powertrain_Transmission_Temperature;
  alias Vehicle_Powertrain_Transmission_TorqueDistribution for SignalDefinitions::Vehicle_Powertrain_Transmission_TorqueDistribution;
  alias Vehicle_Powertrain_Transmission_TravelledDistance for SignalDefinitions::Vehicle_Powertrain_Transmission_TravelledDistance;
  alias Vehicle_Powertrain_Transmission_Type for SignalDefinitions::Vehicle_Powertrain_Transmission_Type;
  alias Vehicle_Powertrain_Type for SignalDefinitions::Vehicle_Powertrain_Type;
  alias Vehicle_RoofLoad for SignalDefinitions::Vehicle_RoofLoad;
  alias Vehicle_Safety_IsFire for SignalDefinitions::Vehicle_Safety_IsFire;
  alias Vehicle_Safety_IsSubmersed for SignalDefinitions::Vehicle_Safety_IsSubmersed;
  alias Vehicle_Safety_Rollover for SignalDefinitions::Vehicle_Safety_Rollover;
  alias Vehicle_Service_DistanceToService for SignalDefinitions::Vehicle_Service_DistanceToService;
  alias Vehicle_Service_IsServiceDue for SignalDefinitions::Vehicle_Service_IsServiceDue;
  alias Vehicle_Service_TimeToService for SignalDefinitions::Vehicle_Service_TimeToService;
  alias Vehicle_Speed for SignalDefinitions::Vehicle_Speed;
  alias Vehicle_StartTime for SignalDefinitions::Vehicle_StartTime;
  alias Vehicle_Trailer_IsConnected for SignalDefinitions::Vehicle_Trailer_IsConnected;
  alias Vehicle_TraveledDistance for SignalDefinitions::Vehicle_TraveledDistance;
  alias Vehicle_TraveledDistanceSinceStart for SignalDefinitions::Vehicle_TraveledDistanceSinceStart;
  alias Vehicle_TripDuration for SignalDefinitions::Vehicle_TripDuration;
  alias Vehicle_TripMeterReading for SignalDefinitions::Vehicle_TripMeterReading;
  alias Vehicle_TurningDiameter for SignalDefinitions::Vehicle_TurningDiameter;
  alias Vehicle_VehicleIdentification_AcrissCode for SignalDefinitions::Vehicle_VehicleIdentification_AcrissCode;
  alias Vehicle_VehicleIdentification_BodyType for SignalDefinitions::Vehicle_VehicleIdentification_BodyType;
  alias Vehicle_VehicleIdentification_Brand for SignalDefinitions::Vehicle_VehicleIdentification_Brand;
  alias Vehicle_VehicleIdentification_DateVehicleFirstRegistered for SignalDefinitions::Vehicle_VehicleIdentification_DateVehicleFirstRegistered;
  alias Vehicle_VehicleIdentification_KnownVehicleDamages for SignalDefinitions::Vehicle_VehicleIdentification_KnownVehicleDamages;
  alias Vehicle_VehicleIdentification_LicensePlate for SignalDefinitions::Vehicle_VehicleIdentification_LicensePlate;
  alias Vehicle_VehicleIdentification_MeetsEmissionStandard for SignalDefinitions::Vehicle_VehicleIdentification_MeetsEmissionStandard;
  alias Vehicle_VehicleIdentification_Model for SignalDefinitions::Vehicle_VehicleIdentification_Model;
  alias Vehicle_VehicleIdentification_OptionalExtras for SignalDefinitions::Vehicle_VehicleIdentification_OptionalExtras;
  alias Vehicle_VehicleIdentification_ProductionDate for SignalDefinitions::Vehicle_VehicleIdentification_ProductionDate;
  alias Vehicle_VehicleIdentification_PurchaseDate for SignalDefinitions::Vehicle_VehicleIdentification_PurchaseDate;
  alias Vehicle_VehicleIdentification_VIN for SignalDefinitions::Vehicle_VehicleIdentification_VIN;
  alias Vehicle_VehicleIdentification_VehicleConfiguration for SignalDefinitions::Vehicle_VehicleIdentification_VehicleConfiguration;
  alias Vehicle_VehicleIdentification_VehicleExteriorColor for SignalDefinitions::Vehicle_VehicleIdentification_VehicleExteriorColor;
  alias Vehicle_VehicleIdentification_VehicleInteriorColor for SignalDefinitions::Vehicle_VehicleIdentification_VehicleInteriorColor;
  alias Vehicle_VehicleIdentification_VehicleInteriorType for SignalDefinitions::Vehicle_VehicleIdentification_VehicleInteriorType;
  alias Vehicle_VehicleIdentification_VehicleModelDate for SignalDefinitions::Vehicle_VehicleIdentification_VehicleModelDate;
  alias Vehicle_VehicleIdentification_VehicleSeatingCapacity for SignalDefinitions::Vehicle_VehicleIdentification_VehicleSeatingCapacity;
  alias Vehicle_VehicleIdentification_VehicleSpecialUsage for SignalDefinitions::Vehicle_VehicleIdentification_VehicleSpecialUsage;
  alias Vehicle_VehicleIdentification_WMI for SignalDefinitions::Vehicle_VehicleIdentification_WMI;
  alias Vehicle_VehicleIdentification_Year for SignalDefinitions::Vehicle_VehicleIdentification_Year;
  alias Vehicle_VersionVSS_Label for SignalDefinitions::Vehicle_VersionVSS_Label;
  alias Vehicle_VersionVSS_Major for SignalDefinitions::Vehicle_VersionVSS_Major;
  alias Vehicle_VersionVSS_Minor for SignalDefinitions::Vehicle_VersionVSS_Minor;
  alias Vehicle_VersionVSS_Patch for SignalDefinitions::Vehicle_VersionVSS_Patch;
  alias Vehicle_WidthExcludingMirrors for SignalDefinitions::Vehicle_WidthExcludingMirrors;
  alias Vehicle_WidthFoldedMirrors for SignalDefinitions::Vehicle_WidthFoldedMirrors;
  alias Vehicle_WidthIncludingMirrors for SignalDefinitions::Vehicle_WidthIncludingMirrors;
}

}
