/*
 * SPDX-License-Identifier: MPL-2.0
 * Generated SysML v2 textual library for COVESA Vehicle Signal Specification (VSS).
 * Source: https://github.com/COVESA/vehicle_signal_specification/tree/20c609bf95c73b51d483fb8f81a099d1d5b73066/spec
 * Scope: leaf VSS attributes, sensors, and actuators reachable from spec/VehicleSignalSpecification.vspec.
 * Unit policy: VSS unit/quantity YAML files are not imported; unit references below point to SysML v2 standard
 * quantity/unit libraries (ISQ/SI/USCustomaryUnits) or derived expressions over those libraries.
 * Semantics policy: VSS path, kind, datatype, description, comment, quantity/unit, range, and allowed-value
 * fields are promoted into SysML metadata annotations instead of being kept only in comments.
 */

library package COVESA_VSS {

private import ScalarValues::*;
private import ISQ::*;
private import SI::*;
private import USCustomaryUnits::*;
private import Metaobjects::SemanticMetadata;

package MetadataDefinitions {
  metadata def VssSignalMetadata :> SemanticMetadata {
    ref :>> annotatedElement : SysML::AttributeDefinition;
    attribute path : String;
    attribute kind : String;
    attribute datatype : String;
    attribute sourceDescription : String;
    attribute sourceComment : String;
  }

  metadata def VssQuantityMetadata :> SemanticMetadata {
    ref :>> annotatedElement : SysML::AttributeDefinition;
    attribute quantityReference : String;
    attribute unitReference : String;
  }

  metadata def VssRangeMetadata :> SemanticMetadata {
    ref :>> annotatedElement : SysML::AttributeDefinition;
    attribute minValue : String;
    attribute maxValue : String;
  }

  metadata def VssAllowedValuesMetadata :> SemanticMetadata {
    ref :>> annotatedElement : SysML::AttributeDefinition;
    attribute allowedValues : String;
  }
}

package AllowedValueDefinitions {
  enum def Vehicle_ADAS_ActiveAutonomyLevel_AllowedValue {
    SAE_0;
    SAE_1;
    SAE_2_DISENGAGING;
    SAE_2;
    SAE_3_DISENGAGING;
    SAE_3;
    SAE_4_DISENGAGING;
    SAE_4;
    SAE_5_DISENGAGING;
    SAE_5;
  }

  enum def Vehicle_ADAS_ObstacleDetection_WarningType_AllowedValue {
    UNDEFINED;
    CROSS_TRAFFIC;
    BLIND_SPOT;
  }

  enum def Vehicle_ADAS_SupportedAutonomyLevel_AllowedValue {
    SAE_0;
    SAE_1;
    SAE_2;
    SAE_3;
    SAE_4;
    SAE_5;
  }

  enum def Vehicle_Body_Hood_Switch_AllowedValue {
    INACTIVE;
    CLOSE;
    OPEN;
    ONE_SHOT_CLOSE;
    ONE_SHOT_OPEN;
  }

  enum def Vehicle_Body_Lights_Brake_IsActive_AllowedValue {
    INACTIVE;
    ACTIVE;
    ADAPTIVE;
  }

  enum def Vehicle_Body_Lights_LightSwitch_AllowedValue {
    OFF;
    POSITION;
    DAYTIME_RUNNING_LIGHTS;
    AUTO;
    BEAM;
  }

  enum def Vehicle_Body_Trunk_Switch_AllowedValue {
    INACTIVE;
    CLOSE;
    OPEN;
    ONE_SHOT_CLOSE;
    ONE_SHOT_OPEN;
  }

  enum def Vehicle_Body_Windshield_Wiping_Mode_AllowedValue {
    OFF;
    SLOW;
    MEDIUM;
    FAST;
    INTERVAL;
    RAIN_SENSOR;
  }

  enum def Vehicle_Body_Windshield_Wiping_System_Mode_AllowedValue {
    STOP_HOLD;
    WIPE;
    PLANT_MODE;
    EMERGENCY_STOP;
  }

  enum def Vehicle_Cabin_Convertible_Status_AllowedValue {
    UNDEFINED;
    CLOSED;
    OPEN;
    CLOSING;
    OPENING;
    STALLED;
  }

  enum def Vehicle_Cabin_Door_Shade_Switch_AllowedValue {
    INACTIVE;
    CLOSE;
    OPEN;
    ONE_SHOT_CLOSE;
    ONE_SHOT_OPEN;
  }

  enum def Vehicle_Cabin_Door_Switch_AllowedValue {
    INACTIVE;
    CLOSE;
    OPEN;
    ONE_SHOT_CLOSE;
    ONE_SHOT_OPEN;
  }

  enum def Vehicle_Cabin_Door_Window_Switch_AllowedValue {
    INACTIVE;
    CLOSE;
    OPEN;
    ONE_SHOT_CLOSE;
    ONE_SHOT_OPEN;
  }

  enum def Vehicle_Cabin_DriverPosition_AllowedValue {
    LEFT;
    MIDDLE;
    RIGHT;
  }

  enum def Vehicle_Cabin_HVAC_Station_AirDistribution_AllowedValue {
    UP;
    MIDDLE;
    DOWN;
  }

  enum def Vehicle_Cabin_Infotainment_HMI_DateFormat_AllowedValue {
    YYYY_MM_DD;
    DD_MM_YYYY;
    MM_DD_YYYY;
    YY_MM_DD;
    DD_MM_YY;
    MM_DD_YY;
  }

  enum def Vehicle_Cabin_Infotainment_HMI_DayNightMode_AllowedValue {
    DAY;
    NIGHT;
  }

  enum def Vehicle_Cabin_Infotainment_HMI_DistanceUnit_AllowedValue {
    MILES;
    KILOMETERS;
  }

  enum def Vehicle_Cabin_Infotainment_HMI_EVEconomyUnits_AllowedValue {
    MILES_PER_KILOWATT_HOUR;
    KILOMETERS_PER_KILOWATT_HOUR;
    KILOWATT_HOURS_PER_100_MILES;
    KILOWATT_HOURS_PER_100_KILOMETERS;
    WATT_HOURS_PER_MILE;
    WATT_HOURS_PER_KILOMETER;
  }

  enum def Vehicle_Cabin_Infotainment_HMI_EVEnergyUnits_AllowedValue {
    WATT_HOURS;
    AMPERE_HOURS;
    KILOWATT_HOURS;
  }

  enum def Vehicle_Cabin_Infotainment_HMI_FontSize_AllowedValue {
    STANDARD;
    LARGE;
    EXTRA_LARGE;
  }

  enum def Vehicle_Cabin_Infotainment_HMI_FuelEconomyUnits_AllowedValue {
    MPG_UK;
    MPG_US;
    MILES_PER_LITER;
    KILOMETERS_PER_LITER;
    LITERS_PER_100_KILOMETERS;
  }

  enum def Vehicle_Cabin_Infotainment_HMI_FuelVolumeUnit_AllowedValue {
    LITER;
    GALLON_US;
    GALLON_UK;
  }

  enum def Vehicle_Cabin_Infotainment_HMI_SpeedUnit_AllowedValue {
    METERS_PER_SECOND;
    MILES_PER_HOUR;
    KILOMETERS_PER_HOUR;
  }

  enum def Vehicle_Cabin_Infotainment_HMI_TemperatureUnit_AllowedValue {
    C;
    F;
  }

  enum def Vehicle_Cabin_Infotainment_HMI_TimeFormat_AllowedValue {
    HR_12;
    HR_24;
  }

  enum def Vehicle_Cabin_Infotainment_HMI_TirePressureUnit_AllowedValue {
    PSI;
    KPA;
    BAR;
  }

  enum def Vehicle_Cabin_Infotainment_Media_Action_AllowedValue {
    UNKNOWN;
    STOP;
    PLAY;
    FAST_FORWARD;
    FAST_BACKWARD;
    SKIP_FORWARD;
    SKIP_BACKWARD;
  }

  enum def Vehicle_Cabin_Infotainment_Media_Played_Source_AllowedValue {
    UNKNOWN;
    SIRIUS_XM;
    AM;
    FM;
    DAB;
    TV;
    CD;
    DVD;
    AUX;
    USB;
    DISK;
    BLUETOOTH;
    INTERNET;
    VOICE;
    BEEP;
  }

  enum def Vehicle_Cabin_Infotainment_Navigation_GuidanceVoice_AllowedValue {
    STANDARD_MALE;
    STANDARD_FEMALE;
    ETC;
  }

  enum def Vehicle_Cabin_Infotainment_Navigation_Mute_AllowedValue {
    MUTED;
    ALERT_ONLY;
    UNMUTED;
  }

  enum def Vehicle_Cabin_Infotainment_SmartphoneProjection_Active_AllowedValue {
    NONE;
    ACTIVE;
    INACTIVE;
  }

  enum def Vehicle_Cabin_Infotainment_SmartphoneProjection_Source_AllowedValue {
    USB;
    BLUETOOTH;
    WIFI;
  }

  enum def Vehicle_Cabin_Infotainment_SmartphoneProjection_SupportedMode_AllowedValue {
    ANDROID_AUTO;
    APPLE_CARPLAY;
    MIRROR_LINK;
    OTHER;
  }

  enum def Vehicle_Cabin_Infotainment_SmartphoneScreenMirroring_Active_AllowedValue {
    NONE;
    ACTIVE;
    INACTIVE;
  }

  enum def Vehicle_Cabin_Infotainment_SmartphoneScreenMirroring_Source_AllowedValue {
    USB;
    BLUETOOTH;
    WIFI;
  }

  enum def Vehicle_Cabin_RearShade_Switch_AllowedValue {
    INACTIVE;
    CLOSE;
    OPEN;
    ONE_SHOT_CLOSE;
    ONE_SHOT_OPEN;
  }

  enum def Vehicle_Cabin_Seat_Massage_Status_AllowedValue {
    ON;
    OFF;
  }

  enum def Vehicle_Cabin_Seat_OccupancyStatus_AllowedValue {
    UNKNOWN;
    OCCUPIED;
    EMPTY;
  }

  enum def Vehicle_Cabin_Sunroof_Shade_Switch_AllowedValue {
    INACTIVE;
    CLOSE;
    OPEN;
    ONE_SHOT_CLOSE;
    ONE_SHOT_OPEN;
  }

  enum def Vehicle_Cabin_Sunroof_Switch_AllowedValue {
    INACTIVE;
    CLOSE;
    OPEN;
    ONE_SHOT_CLOSE;
    ONE_SHOT_OPEN;
    TILT_UP;
    TILT_DOWN;
  }

  enum def Vehicle_CurrentLocation_GNSSReceiver_FixType_AllowedValue {
    NONE;
    TWO_D;
    TWO_D_SATELLITE_BASED_AUGMENTATION;
    TWO_D_GROUND_BASED_AUGMENTATION;
    TWO_D_SATELLITE_AND_GROUND_BASED_AUGMENTATION;
    THREE_D;
    THREE_D_SATELLITE_BASED_AUGMENTATION;
    THREE_D_GROUND_BASED_AUGMENTATION;
    THREE_D_SATELLITE_AND_GROUND_BASED_AUGMENTATION;
  }

  enum def Vehicle_LowVoltageSystemState_AllowedValue {
    UNDEFINED;
    LOCK;
    OFF;
    ACC;
    ON;
    START;
  }

  enum def Vehicle_Powertrain_CombustionEngine_AspirationType_AllowedValue {
    UNKNOWN;
    NATURAL;
    SUPERCHARGER;
    TURBOCHARGER;
  }

  enum def Vehicle_Powertrain_CombustionEngine_Configuration_AllowedValue {
    UNKNOWN;
    STRAIGHT;
    V;
    BOXER;
    W;
    ROTARY;
    RADIAL;
    SQUARE;
    H;
    U;
    OPPOSED;
    X;
  }

  enum def Vehicle_Powertrain_CombustionEngine_EngineCoolant_Level_AllowedValue {
    CRITICALLY_LOW;
    LOW;
    NORMAL;
  }

  enum def Vehicle_Powertrain_CombustionEngine_EngineOil_Level_AllowedValue {
    CRITICALLY_LOW;
    LOW;
    NORMAL;
    HIGH;
    CRITICALLY_HIGH;
  }

  enum def Vehicle_Powertrain_ElectricMotor_EngineCoolant_Level_AllowedValue {
    CRITICALLY_LOW;
    LOW;
    NORMAL;
  }

  enum def Vehicle_Powertrain_FuelSystem_HybridType_AllowedValue {
    UNKNOWN;
    NOT_APPLICABLE;
    STOP_START;
    BELT_ISG;
    CIMG;
    PHEV;
  }

  enum def Vehicle_Powertrain_FuelSystem_RefuelPortPosition_AllowedValue {
    FRONT_LEFT;
    FRONT_MIDDLE;
    FRONT_RIGHT;
    REAR_LEFT;
    REAR_MIDDLE;
    REAR_RIGHT;
    LEFT_FRONT;
    LEFT_MIDDLE;
    LEFT_REAR;
    RIGHT_FRONT;
    RIGHT_MIDDLE;
    RIGHT_REAR;
  }

  enum def Vehicle_Powertrain_FuelSystem_SupportedFuel_AllowedValue {
    E5_95;
    E5_98;
    E10_95;
    E10_98;
    E85;
    B7;
    B10;
    B20;
    B30;
    B100;
    XTL;
    LPG;
    CNG;
    LNG;
    H2;
    OTHER;
  }

  enum def Vehicle_Powertrain_FuelSystem_SupportedFuelTypes_AllowedValue {
    GASOLINE;
    DIESEL;
    E85;
    LPG;
    CNG;
    LNG;
    H2;
    OTHER;
  }

  enum def Vehicle_Powertrain_RangeExtender_OperatingMode_AllowedValue {
    CHARGE_DEPLETING;
    CHARGE_SUSTAINING;
    BLENDED;
  }

  enum def Vehicle_Powertrain_TractionBattery_BatteryConditioning_RequestedMode_AllowedValue {
    INACTIVE;
    FAST_CHARGING_PREPARATION;
    DRIVING_PREPARATION;
  }

  enum def Vehicle_Powertrain_TractionBattery_Charging_ChargingPort_SupportedInletTypes_AllowedValue {
    IEC_TYPE_1_AC;
    IEC_TYPE_2_AC;
    IEC_TYPE_3_AC;
    IEC_TYPE_4_DC;
    IEC_TYPE_1_CCS_DC;
    IEC_TYPE_2_CCS_DC;
    TESLA_ROADSTER;
    TESLA_HPWC;
    TESLA_SUPERCHARGER;
    GBT_AC;
    GBT_DC;
    OTHER;
  }

  enum def Vehicle_Powertrain_TractionBattery_Charging_StartStopCharging_AllowedValue {
    START;
    STOP;
  }

  enum def Vehicle_Powertrain_TractionBattery_Charging_Timer_Mode_AllowedValue {
    INACTIVE;
    START_TIME;
    END_TIME;
  }

  enum def Vehicle_Powertrain_Transmission_DriveType_AllowedValue {
    UNKNOWN;
    FORWARD_WHEEL_DRIVE;
    REAR_WHEEL_DRIVE;
    ALL_WHEEL_DRIVE;
  }

  enum def Vehicle_Powertrain_Transmission_GearChangeMode_AllowedValue {
    MANUAL;
    AUTOMATIC;
  }

  enum def Vehicle_Powertrain_Transmission_PerformanceMode_AllowedValue {
    NORMAL;
    SPORT;
    ECONOMY;
    SNOW;
    RAIN;
  }

  enum def Vehicle_Powertrain_Transmission_Type_AllowedValue {
    UNKNOWN;
    SEQUENTIAL;
    H;
    AUTOMATIC;
    DSG;
    CVT;
  }

  enum def Vehicle_Powertrain_Type_AllowedValue {
    COMBUSTION;
    HYBRID;
    ELECTRIC;
  }

}

package SignalDefinitions {
  private import COVESA_VSS::MetadataDefinitions::*;
  private import COVESA_VSS::AllowedValueDefinitions::*;

  attribute def Vehicle_ADAS_ABS_IsEnabled :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_ABS_IsEnabled {
    path = "Vehicle.ADAS.ABS.IsEnabled";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Indicates if ABS is enabled. True = Enabled. False = Disabled.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_ABS_IsEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_ABS_IsEngaged {
    path = "Vehicle.ADAS.ABS.IsEngaged";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if ABS is currently regulating brake pressure. True = Engaged. False = Not Engaged.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_ABS_IsError :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_ABS_IsError {
    path = "Vehicle.ADAS.ABS.IsError";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if ABS incurred an error condition. True = Error. False = No Error.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_ActiveAutonomyLevel :> Vehicle_ADAS_ActiveAutonomyLevel_AllowedValue;
  @VssSignalMetadata about Vehicle_ADAS_ActiveAutonomyLevel {
    path = "Vehicle.ADAS.ActiveAutonomyLevel";
    kind = "sensor";
    datatype = "string";
    sourceDescription = "Indicates the currently active level of driving automation according to the SAE J3016 (Taxonomy and Definitions for Terms Related to Driving Automation Systems for On-Road Motor Vehicles).";
    sourceComment = "Complies with https://www.sae.org/standards/content/j3016_202104/ and https://www.sae.org/blog/sae-j3016-update. Level 5 and 4 ADS (Automated driving system) disengage, if appropriate, only after it achieves a minimal risk condition or a driver is performing the DDT. Level 3 ADS disengages either an appropriate time after issuing a request to intervene or immediately upon user request. Level 2 DAS (Driving automation system) disengages immediately upon driver request. However, since many Level 2 DAS, often termed \"Level 2.5\", warn the driver shortly before reaching their operational limits, the VSS also supports the DISENGAGING state for SAE_2. Nevertheless, it should be noted that the SAE J3016 states that it is incorrect to describe driving automation features using fractional levels.";
  }
  @VssAllowedValuesMetadata about Vehicle_ADAS_ActiveAutonomyLevel {
    allowedValues = "SAE_0, SAE_1, SAE_2_DISENGAGING, SAE_2, SAE_3_DISENGAGING, SAE_3, SAE_4_DISENGAGING, SAE_4, SAE_5_DISENGAGING, SAE_5";
  }

  attribute def Vehicle_ADAS_CruiseControl_AdaptiveDistanceSet :> Real;
  @VssSignalMetadata about Vehicle_ADAS_CruiseControl_AdaptiveDistanceSet {
    path = "Vehicle.ADAS.CruiseControl.AdaptiveDistanceSet";
    kind = "actuator";
    datatype = "float";
    sourceDescription = "Distance in meters to keep from lead vehicle";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_ADAS_CruiseControl_AdaptiveDistanceSet {
    quantityReference = "ISQ::length";
    unitReference = "SI::metre";
  }
  @VssRangeMetadata about Vehicle_ADAS_CruiseControl_AdaptiveDistanceSet {
    minValue = "0.0";
    maxValue = "";
  }

  attribute def Vehicle_ADAS_CruiseControl_AdaptiveIntervalSet :> Integer;
  @VssSignalMetadata about Vehicle_ADAS_CruiseControl_AdaptiveIntervalSet {
    path = "Vehicle.ADAS.CruiseControl.AdaptiveIntervalSet";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Follow distance setting, commonly 1-5 with 1 being closest.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_CruiseControl_IsActive :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_CruiseControl_IsActive {
    path = "Vehicle.ADAS.CruiseControl.IsActive";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Indicates if cruise control system is active (i.e. actively controls speed). True = Active. False = Inactive.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_CruiseControl_IsAdaptive :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_CruiseControl_IsAdaptive {
    path = "Vehicle.ADAS.CruiseControl.IsAdaptive";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Indicates if cruise control system is adaptive (i.e. actively controls speed).";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_CruiseControl_IsEnabled :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_CruiseControl_IsEnabled {
    path = "Vehicle.ADAS.CruiseControl.IsEnabled";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Indicates if cruise control system is enabled (e.g. ready to receive configurations and settings) True = Enabled. False = Disabled.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_CruiseControl_IsError :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_CruiseControl_IsError {
    path = "Vehicle.ADAS.CruiseControl.IsError";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if cruise control system incurred an error condition. True = Error. False = No Error.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_CruiseControl_SpeedSet :> Real;
  @VssSignalMetadata about Vehicle_ADAS_CruiseControl_SpeedSet {
    path = "Vehicle.ADAS.CruiseControl.SpeedSet";
    kind = "actuator";
    datatype = "float";
    sourceDescription = "Set cruise control speed in kilometers per hour.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_ADAS_CruiseControl_SpeedSet {
    quantityReference = "ISQ::speed";
    unitReference = "SI::kilometrePerHour";
  }

  attribute def Vehicle_ADAS_DMS_IsEnabled :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_DMS_IsEnabled {
    path = "Vehicle.ADAS.DMS.IsEnabled";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Indicates if DMS is enabled. True = Enabled. False = Disabled.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_DMS_IsError :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_DMS_IsError {
    path = "Vehicle.ADAS.DMS.IsError";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if DMS incurred an error condition. True = Error. False = No Error.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_DMS_IsWarning :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_DMS_IsWarning {
    path = "Vehicle.ADAS.DMS.IsWarning";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if DMS has registered a driver alert condition.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_EBA_IsEnabled :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_EBA_IsEnabled {
    path = "Vehicle.ADAS.EBA.IsEnabled";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Indicates if EBA is enabled. True = Enabled. False = Disabled.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_EBA_IsEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_EBA_IsEngaged {
    path = "Vehicle.ADAS.EBA.IsEngaged";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if EBA is currently regulating brake pressure. True = Engaged. False = Not Engaged.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_EBA_IsError :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_EBA_IsError {
    path = "Vehicle.ADAS.EBA.IsError";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if EBA incurred an error condition. True = Error. False = No Error.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_EBD_IsEnabled :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_EBD_IsEnabled {
    path = "Vehicle.ADAS.EBD.IsEnabled";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Indicates if EBD is enabled. True = Enabled. False = Disabled.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_EBD_IsEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_EBD_IsEngaged {
    path = "Vehicle.ADAS.EBD.IsEngaged";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if EBD is currently regulating vehicle brakeforce distribution. True = Engaged. False = Not Engaged.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_EBD_IsError :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_EBD_IsError {
    path = "Vehicle.ADAS.EBD.IsError";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if EBD incurred an error condition. True = Error. False = No Error.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_ESC_IsEnabled :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_ESC_IsEnabled {
    path = "Vehicle.ADAS.ESC.IsEnabled";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Indicates if ESC is enabled. True = Enabled. False = Disabled.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_ESC_IsEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_ESC_IsEngaged {
    path = "Vehicle.ADAS.ESC.IsEngaged";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if ESC is currently regulating vehicle stability. True = Engaged. False = Not Engaged.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_ESC_IsError :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_ESC_IsError {
    path = "Vehicle.ADAS.ESC.IsError";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if ESC incurred an error condition. True = Error. False = No Error.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_ESC_IsStrongCrossWindDetected :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_ESC_IsStrongCrossWindDetected {
    path = "Vehicle.ADAS.ESC.IsStrongCrossWindDetected";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if the ESC system is detecting strong cross winds. True = Strong cross winds detected. False = No strong cross winds detected.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_ESC_RoadFriction_LowerBound :> Real;
  @VssSignalMetadata about Vehicle_ADAS_ESC_RoadFriction_LowerBound {
    path = "Vehicle.ADAS.ESC.RoadFriction.LowerBound";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Lower bound road friction, as calculated by the ESC system. 5% possibility that road friction is below this value. 0 = no friction, 100 = maximum friction.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_ADAS_ESC_RoadFriction_LowerBound {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_ADAS_ESC_RoadFriction_LowerBound {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_ADAS_ESC_RoadFriction_MostProbable :> Real;
  @VssSignalMetadata about Vehicle_ADAS_ESC_RoadFriction_MostProbable {
    path = "Vehicle.ADAS.ESC.RoadFriction.MostProbable";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Most probable road friction, as calculated by the ESC system. Exact meaning of most probable is implementation specific. 0 = no friction, 100 = maximum friction.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_ADAS_ESC_RoadFriction_MostProbable {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_ADAS_ESC_RoadFriction_MostProbable {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_ADAS_ESC_RoadFriction_UpperBound :> Real;
  @VssSignalMetadata about Vehicle_ADAS_ESC_RoadFriction_UpperBound {
    path = "Vehicle.ADAS.ESC.RoadFriction.UpperBound";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Upper bound road friction, as calculated by the ESC system. 95% possibility that road friction is below this value. 0 = no friction, 100 = maximum friction.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_ADAS_ESC_RoadFriction_UpperBound {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_ADAS_ESC_RoadFriction_UpperBound {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_ADAS_IsAutoPowerOptimize :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_IsAutoPowerOptimize {
    path = "Vehicle.ADAS.IsAutoPowerOptimize";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Auto Power Optimization Flag When set to 'true', the system enables automatic power optimization, dynamically adjusting the power optimization level based on runtime conditions or features managed by the OEM. When set to 'false', manual control of the power optimization level is allowed.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_LaneDepartureDetection_IsEnabled :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_LaneDepartureDetection_IsEnabled {
    path = "Vehicle.ADAS.LaneDepartureDetection.IsEnabled";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Indicates if lane departure detection system is enabled. True = Enabled. False = Disabled.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_LaneDepartureDetection_IsError :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_LaneDepartureDetection_IsError {
    path = "Vehicle.ADAS.LaneDepartureDetection.IsError";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if lane departure system incurred an error condition. True = Error. False = No Error.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_LaneDepartureDetection_IsWarning :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_LaneDepartureDetection_IsWarning {
    path = "Vehicle.ADAS.LaneDepartureDetection.IsWarning";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if lane departure detection registered a lane departure.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_ObstacleDetection_Distance :> Real;
  @VssSignalMetadata about Vehicle_ADAS_ObstacleDetection_Distance {
    path = "Vehicle.ADAS.ObstacleDetection.Distance";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Distance in meters to detected object";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_ADAS_ObstacleDetection_Distance {
    quantityReference = "ISQ::length";
    unitReference = "SI::metre";
  }
  @VssRangeMetadata about Vehicle_ADAS_ObstacleDetection_Distance {
    minValue = "0.0";
    maxValue = "";
  }

  attribute def Vehicle_ADAS_ObstacleDetection_IsEnabled :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_ObstacleDetection_IsEnabled {
    path = "Vehicle.ADAS.ObstacleDetection.IsEnabled";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Indicates if obstacle sensor system is enabled (i.e. monitoring for obstacles). True = Enabled. False = Disabled.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_ObstacleDetection_IsError :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_ObstacleDetection_IsError {
    path = "Vehicle.ADAS.ObstacleDetection.IsError";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if obstacle sensor system incurred an error condition. True = Error. False = No Error.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_ObstacleDetection_IsWarning :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_ObstacleDetection_IsWarning {
    path = "Vehicle.ADAS.ObstacleDetection.IsWarning";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if obstacle sensor system registered an obstacle.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_ObstacleDetection_TimeGap :> Integer;
  @VssSignalMetadata about Vehicle_ADAS_ObstacleDetection_TimeGap {
    path = "Vehicle.ADAS.ObstacleDetection.TimeGap";
    kind = "sensor";
    datatype = "uint32";
    sourceDescription = "Time in milliseconds before potential impact object";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_ADAS_ObstacleDetection_TimeGap {
    quantityReference = "ISQ::time";
    unitReference = "SI::millisecond";
  }

  attribute def Vehicle_ADAS_ObstacleDetection_WarningType :> Vehicle_ADAS_ObstacleDetection_WarningType_AllowedValue;
  @VssSignalMetadata about Vehicle_ADAS_ObstacleDetection_WarningType {
    path = "Vehicle.ADAS.ObstacleDetection.WarningType";
    kind = "sensor";
    datatype = "string";
    sourceDescription = "Indicates the type of obstacle warning detected as some track not only the presence of an obstacle but potential intercepting trajectory or other characteristics.";
    sourceComment = "Undefined obstacle warning type would merely alert of presence of obstacle and may measure distance.";
  }
  @VssAllowedValuesMetadata about Vehicle_ADAS_ObstacleDetection_WarningType {
    allowedValues = "UNDEFINED, CROSS_TRAFFIC, BLIND_SPOT";
  }

  attribute def Vehicle_ADAS_PowerOptimizeLevel :> Integer;
  @VssSignalMetadata about Vehicle_ADAS_PowerOptimizeLevel {
    path = "Vehicle.ADAS.PowerOptimizeLevel";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Power optimization level for this branch/subsystem. A higher number indicates more aggressive power optimization. Level 0 indicates that all functionality is enabled, no power optimization enabled. Level 10 indicates most aggressive power optimization mode, only essential functionality enabled.";
    sourceComment = "";
  }
  @VssRangeMetadata about Vehicle_ADAS_PowerOptimizeLevel {
    minValue = "0";
    maxValue = "10";
  }

  attribute def Vehicle_ADAS_SupportedAutonomyLevel :> Vehicle_ADAS_SupportedAutonomyLevel_AllowedValue;
  @VssSignalMetadata about Vehicle_ADAS_SupportedAutonomyLevel {
    path = "Vehicle.ADAS.SupportedAutonomyLevel";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "Indicates the highest level of driving automation according to the SAE J3016 taxonomy the vehicle is capable of.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_ADAS_SupportedAutonomyLevel {
    allowedValues = "SAE_0, SAE_1, SAE_2, SAE_3, SAE_4, SAE_5";
  }

  attribute def Vehicle_ADAS_TCS_IsEnabled :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_TCS_IsEnabled {
    path = "Vehicle.ADAS.TCS.IsEnabled";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Indicates if TCS is enabled. True = Enabled. False = Disabled.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_TCS_IsEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_TCS_IsEngaged {
    path = "Vehicle.ADAS.TCS.IsEngaged";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if TCS is currently regulating traction. True = Engaged. False = Not Engaged.";
    sourceComment = "";
  }

  attribute def Vehicle_ADAS_TCS_IsError :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_TCS_IsError {
    path = "Vehicle.ADAS.TCS.IsError";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if TCS incurred an error condition. True = Error. False = No Error.";
    sourceComment = "";
  }

  attribute def Vehicle_Acceleration_Lateral :> Real;
  @VssSignalMetadata about Vehicle_Acceleration_Lateral {
    path = "Vehicle.Acceleration.Lateral";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Vehicle acceleration in Y (lateral acceleration).";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Acceleration_Lateral {
    quantityReference = "ISQ::acceleration";
    unitReference = "SI::metrePerSecondSquared";
  }

  attribute def Vehicle_Acceleration_Longitudinal :> Real;
  @VssSignalMetadata about Vehicle_Acceleration_Longitudinal {
    path = "Vehicle.Acceleration.Longitudinal";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Vehicle acceleration in X (longitudinal acceleration).";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Acceleration_Longitudinal {
    quantityReference = "ISQ::acceleration";
    unitReference = "SI::metrePerSecondSquared";
  }

  attribute def Vehicle_Acceleration_Vertical :> Real;
  @VssSignalMetadata about Vehicle_Acceleration_Vertical {
    path = "Vehicle.Acceleration.Vertical";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Vehicle acceleration in Z (vertical acceleration).";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Acceleration_Vertical {
    quantityReference = "ISQ::acceleration";
    unitReference = "SI::metrePerSecondSquared";
  }

  attribute def Vehicle_AngularVelocity_Pitch :> Real;
  @VssSignalMetadata about Vehicle_AngularVelocity_Pitch {
    path = "Vehicle.AngularVelocity.Pitch";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Vehicle rotation rate along Y (lateral).";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_AngularVelocity_Pitch {
    quantityReference = "ISQ::angularVelocity";
    unitReference = "SI::degreePerSecond";
  }

  attribute def Vehicle_AngularVelocity_Roll :> Real;
  @VssSignalMetadata about Vehicle_AngularVelocity_Roll {
    path = "Vehicle.AngularVelocity.Roll";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Vehicle rotation rate along X (longitudinal).";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_AngularVelocity_Roll {
    quantityReference = "ISQ::angularVelocity";
    unitReference = "SI::degreePerSecond";
  }

  attribute def Vehicle_AngularVelocity_Yaw :> Real;
  @VssSignalMetadata about Vehicle_AngularVelocity_Yaw {
    path = "Vehicle.AngularVelocity.Yaw";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Vehicle rotation rate along Z (vertical).";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_AngularVelocity_Yaw {
    quantityReference = "ISQ::angularVelocity";
    unitReference = "SI::degreePerSecond";
  }

  attribute def Vehicle_AverageSpeed :> Real;
  @VssSignalMetadata about Vehicle_AverageSpeed {
    path = "Vehicle.AverageSpeed";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Average speed for the current trip.";
    sourceComment = "A new trip is considered to start when engine gets enabled (e.g. LowVoltageSystemState in ON or START mode). A trip is considered to end when engine is no longer enabled. The signal may however keep the value of the last trip until a new trip is started. Calculation of average speed may exclude periods when the vehicle for example is not moving or transmission is in neutral.";
  }
  @VssQuantityMetadata about Vehicle_AverageSpeed {
    quantityReference = "ISQ::speed";
    unitReference = "SI::kilometrePerHour";
  }

  attribute def Vehicle_Body_BodyType :> String;
  @VssSignalMetadata about Vehicle_Body_BodyType {
    path = "Vehicle.Body.BodyType";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "Body type code as defined by ISO 3779.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Hood_IsOpen :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Hood_IsOpen {
    path = "Vehicle.Body.Hood.IsOpen";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is item open or closed? True = Fully or partially open. False = Fully closed.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Hood_Position :> Integer;
  @VssSignalMetadata about Vehicle_Body_Hood_Position {
    path = "Vehicle.Body.Hood.Position";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Item position. 0 = Start position 100 = End position.";
    sourceComment = "Relationship between Open/Close and Start/End position is item dependent.";
  }
  @VssQuantityMetadata about Vehicle_Body_Hood_Position {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Body_Hood_Position {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Body_Hood_Switch :> Vehicle_Body_Hood_Switch_AllowedValue;
  @VssSignalMetadata about Vehicle_Body_Hood_Switch {
    path = "Vehicle.Body.Hood.Switch";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Switch controlling sliding action such as window, sunroof, or blind.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Body_Hood_Switch {
    allowedValues = "INACTIVE, CLOSE, OPEN, ONE_SHOT_CLOSE, ONE_SHOT_OPEN";
  }

  attribute def Vehicle_Body_Horn_IsActive :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Horn_IsActive {
    path = "Vehicle.Body.Horn.IsActive";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Horn active or inactive. True = Active. False = Inactive.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_IsAutoPowerOptimize :> Boolean;
  @VssSignalMetadata about Vehicle_Body_IsAutoPowerOptimize {
    path = "Vehicle.Body.IsAutoPowerOptimize";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Auto Power Optimization Flag When set to 'true', the system enables automatic power optimization, dynamically adjusting the power optimization level based on runtime conditions or features managed by the OEM. When set to 'false', manual control of the power optimization level is allowed.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Lights_Backup_IsDefect :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Lights_Backup_IsDefect {
    path = "Vehicle.Body.Lights.Backup.IsDefect";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if light is defect. True = Light is defect. False = Light has no defect.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Lights_Backup_IsOn :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Lights_Backup_IsOn {
    path = "Vehicle.Body.Lights.Backup.IsOn";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Indicates if light is on or off. True = On. False = Off.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Lights_Beam_IsDefect :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Lights_Beam_IsDefect {
    path = "Vehicle.Body.Lights.Beam.IsDefect";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if light is defect. True = Light is defect. False = Light has no defect.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Lights_Beam_IsOn :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Lights_Beam_IsOn {
    path = "Vehicle.Body.Lights.Beam.IsOn";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Indicates if light is on or off. True = On. False = Off.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Lights_Brake_IsActive :> Vehicle_Body_Lights_Brake_IsActive_AllowedValue;
  @VssSignalMetadata about Vehicle_Body_Lights_Brake_IsActive {
    path = "Vehicle.Body.Lights.Brake.IsActive";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Indicates if break-light is active. INACTIVE means lights are off. ACTIVE means lights are on. ADAPTIVE means that break-light is indicating emergency-breaking.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Body_Lights_Brake_IsActive {
    allowedValues = "INACTIVE, ACTIVE, ADAPTIVE";
  }

  attribute def Vehicle_Body_Lights_Brake_IsDefect :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Lights_Brake_IsDefect {
    path = "Vehicle.Body.Lights.Brake.IsDefect";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if light is defect. True = Light is defect. False = Light has no defect.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Lights_DirectionIndicator_IsDefect :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Lights_DirectionIndicator_IsDefect {
    path = "Vehicle.Body.Lights.DirectionIndicator.IsDefect";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if light is defect. True = Light is defect. False = Light has no defect.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Lights_DirectionIndicator_IsSignaling :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Lights_DirectionIndicator_IsSignaling {
    path = "Vehicle.Body.Lights.DirectionIndicator.IsSignaling";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Indicates if light is signaling or off. True = signaling. False = Off.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Lights_Fog_IsDefect :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Lights_Fog_IsDefect {
    path = "Vehicle.Body.Lights.Fog.IsDefect";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if light is defect. True = Light is defect. False = Light has no defect.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Lights_Fog_IsOn :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Lights_Fog_IsOn {
    path = "Vehicle.Body.Lights.Fog.IsOn";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Indicates if light is on or off. True = On. False = Off.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Lights_Hazard_IsDefect :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Lights_Hazard_IsDefect {
    path = "Vehicle.Body.Lights.Hazard.IsDefect";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if light is defect. True = Light is defect. False = Light has no defect.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Lights_Hazard_IsSignaling :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Lights_Hazard_IsSignaling {
    path = "Vehicle.Body.Lights.Hazard.IsSignaling";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Indicates if light is signaling or off. True = signaling. False = Off.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Lights_IsHighBeamSwitchOn :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Lights_IsHighBeamSwitchOn {
    path = "Vehicle.Body.Lights.IsHighBeamSwitchOn";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Status of the high beam switch. True = high beam enabled. False = high beam not enabled.";
    sourceComment = "This signal indicates the status of the switch and does not indicate if low or high beam actually are on. That typically depends on vehicle logic and other signals like Lights.LightSwitch and Vehicle.LowVoltageSystemState.";
  }

  attribute def Vehicle_Body_Lights_LicensePlate_IsDefect :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Lights_LicensePlate_IsDefect {
    path = "Vehicle.Body.Lights.LicensePlate.IsDefect";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if light is defect. True = Light is defect. False = Light has no defect.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Lights_LicensePlate_IsOn :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Lights_LicensePlate_IsOn {
    path = "Vehicle.Body.Lights.LicensePlate.IsOn";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Indicates if light is on or off. True = On. False = Off.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Lights_LightSwitch :> Vehicle_Body_Lights_LightSwitch_AllowedValue;
  @VssSignalMetadata about Vehicle_Body_Lights_LightSwitch {
    path = "Vehicle.Body.Lights.LightSwitch";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Status of the vehicle main light switch.";
    sourceComment = "A vehicle typically does not support all alternatives. Which lights that actually are lit may vary according to vehicle configuration and local legislation. OFF is typically indicated by 0. POSITION is typically indicated by ISO 7000 symbol 0456. DAYTIME_RUNNING_LIGHTS (DRL) can be indicated by ISO 7000 symbol 2611. AUTO indicates that vehicle automatically selects suitable lights. BEAM is typically indicated by ISO 7000 symbol 0083.";
  }
  @VssAllowedValuesMetadata about Vehicle_Body_Lights_LightSwitch {
    allowedValues = "OFF, POSITION, DAYTIME_RUNNING_LIGHTS, AUTO, BEAM";
  }

  attribute def Vehicle_Body_Lights_Parking_IsDefect :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Lights_Parking_IsDefect {
    path = "Vehicle.Body.Lights.Parking.IsDefect";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if light is defect. True = Light is defect. False = Light has no defect.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Lights_Parking_IsOn :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Lights_Parking_IsOn {
    path = "Vehicle.Body.Lights.Parking.IsOn";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Indicates if light is on or off. True = On. False = Off.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Lights_Running_IsDefect :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Lights_Running_IsDefect {
    path = "Vehicle.Body.Lights.Running.IsDefect";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if light is defect. True = Light is defect. False = Light has no defect.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Lights_Running_IsOn :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Lights_Running_IsOn {
    path = "Vehicle.Body.Lights.Running.IsOn";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Indicates if light is on or off. True = On. False = Off.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Mirrors_IsFolded :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Mirrors_IsFolded {
    path = "Vehicle.Body.Mirrors.IsFolded";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is mirror folded? True = Fully or partially folded. False = Fully unfolded.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Mirrors_IsHeatingOn :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Mirrors_IsHeatingOn {
    path = "Vehicle.Body.Mirrors.IsHeatingOn";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Mirror Heater on or off. True = Heater On. False = Heater Off.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Mirrors_IsLocked :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Mirrors_IsLocked {
    path = "Vehicle.Body.Mirrors.IsLocked";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is mirror movement locked? True = Locked, mirror will not react to Tilt/Pan change. False = Unlocked.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Mirrors_Pan :> Integer;
  @VssSignalMetadata about Vehicle_Body_Mirrors_Pan {
    path = "Vehicle.Body.Mirrors.Pan";
    kind = "actuator";
    datatype = "int8";
    sourceDescription = "Mirror pan as a percent. 0 = Center Position. 100 = Fully Left Position. -100 = Fully Right Position.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Body_Mirrors_Pan {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Body_Mirrors_Pan {
    minValue = "-100";
    maxValue = "100";
  }

  attribute def Vehicle_Body_Mirrors_Tilt :> Integer;
  @VssSignalMetadata about Vehicle_Body_Mirrors_Tilt {
    path = "Vehicle.Body.Mirrors.Tilt";
    kind = "actuator";
    datatype = "int8";
    sourceDescription = "Mirror tilt as a percent. 0 = Center Position. 100 = Fully Upward Position. -100 = Fully Downward Position.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Body_Mirrors_Tilt {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Body_Mirrors_Tilt {
    minValue = "-100";
    maxValue = "100";
  }

  attribute def Vehicle_Body_Mirrors_Yaw :> Integer;
  @VssSignalMetadata about Vehicle_Body_Mirrors_Yaw {
    path = "Vehicle.Body.Mirrors.Yaw";
    kind = "actuator";
    datatype = "int8";
    sourceDescription = "Relative mirror yaw angle, measured from the vehicle sprung mass X-axis as defined by ISO 23150:2023 to the mirror X-axis, around the vehicle Z-axis (right-hand rule). 0 = Mirror in default position. Exact position (yaw relative to vehicle X-axis) is vehicle dependent. 100 = Maximum yaw. Mirror rotated clockwise as much as possible around Z-axis. -100 = Minimum yaw. Mirror rotated counter-clockwise as much as possible around Z-axis.";
    sourceComment = "A positive yaw indicates that the mirror has been adjusted to get a better view on objects on the right side of the vehicle.";
  }
  @VssQuantityMetadata about Vehicle_Body_Mirrors_Yaw {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Body_Mirrors_Yaw {
    minValue = "-100";
    maxValue = "100";
  }

  attribute def Vehicle_Body_PowerOptimizeLevel :> Integer;
  @VssSignalMetadata about Vehicle_Body_PowerOptimizeLevel {
    path = "Vehicle.Body.PowerOptimizeLevel";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Power optimization level for this branch/subsystem. A higher number indicates more aggressive power optimization. Level 0 indicates that all functionality is enabled, no power optimization enabled. Level 10 indicates most aggressive power optimization mode, only essential functionality enabled.";
    sourceComment = "";
  }
  @VssRangeMetadata about Vehicle_Body_PowerOptimizeLevel {
    minValue = "0";
    maxValue = "10";
  }

  attribute def Vehicle_Body_Raindetection_Intensity :> Integer;
  @VssSignalMetadata about Vehicle_Body_Raindetection_Intensity {
    path = "Vehicle.Body.Raindetection.Intensity";
    kind = "sensor";
    datatype = "uint8";
    sourceDescription = "Rain intensity. 0 = Dry, No Rain. 100 = Covered.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Body_Raindetection_Intensity {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Body_Raindetection_Intensity {
    minValue = "";
    maxValue = "100";
  }

  attribute def Vehicle_Body_RearMainSpoilerPosition :> Real;
  @VssSignalMetadata about Vehicle_Body_RearMainSpoilerPosition {
    path = "Vehicle.Body.RearMainSpoilerPosition";
    kind = "actuator";
    datatype = "float";
    sourceDescription = "Rear spoiler position, 0% = Spoiler fully stowed. 100% = Spoiler fully exposed.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Body_RearMainSpoilerPosition {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Body_RearMainSpoilerPosition {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Body_Trunk_IsLightOn :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Trunk_IsLightOn {
    path = "Vehicle.Body.Trunk.IsLightOn";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is trunk light on";
    sourceComment = "V4.0 Moved from Vehicle.Cabin.Lights.IsTrunkOn because Trunk is not defined as part of the Cabin.";
  }

  attribute def Vehicle_Body_Trunk_IsLocked :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Trunk_IsLocked {
    path = "Vehicle.Body.Trunk.IsLocked";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is item locked or unlocked. True = Locked. False = Unlocked.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Trunk_IsOpen :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Trunk_IsOpen {
    path = "Vehicle.Body.Trunk.IsOpen";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is item open or closed? True = Fully or partially open. False = Fully closed.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Trunk_Position :> Integer;
  @VssSignalMetadata about Vehicle_Body_Trunk_Position {
    path = "Vehicle.Body.Trunk.Position";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Item position. 0 = Start position 100 = End position.";
    sourceComment = "Relationship between Open/Close and Start/End position is item dependent.";
  }
  @VssQuantityMetadata about Vehicle_Body_Trunk_Position {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Body_Trunk_Position {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Body_Trunk_Switch :> Vehicle_Body_Trunk_Switch_AllowedValue;
  @VssSignalMetadata about Vehicle_Body_Trunk_Switch {
    path = "Vehicle.Body.Trunk.Switch";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Switch controlling sliding action such as window, sunroof, or blind.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Body_Trunk_Switch {
    allowedValues = "INACTIVE, CLOSE, OPEN, ONE_SHOT_CLOSE, ONE_SHOT_OPEN";
  }

  attribute def Vehicle_Body_Windshield_IsHeatingOn :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Windshield_IsHeatingOn {
    path = "Vehicle.Body.Windshield.IsHeatingOn";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Windshield heater status. False - off, True - on.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Windshield_WasherFluid_IsLevelLow :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Windshield_WasherFluid_IsLevelLow {
    path = "Vehicle.Body.Windshield.WasherFluid.IsLevelLow";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Low level indication for washer fluid. True = Level Low. False = Level OK.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Windshield_WasherFluid_Level :> Integer;
  @VssSignalMetadata about Vehicle_Body_Windshield_WasherFluid_Level {
    path = "Vehicle.Body.Windshield.WasherFluid.Level";
    kind = "sensor";
    datatype = "uint8";
    sourceDescription = "Washer fluid level as a percent. 0 = Empty. 100 = Full.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Body_Windshield_WasherFluid_Level {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Body_Windshield_WasherFluid_Level {
    minValue = "";
    maxValue = "100";
  }

  attribute def Vehicle_Body_Windshield_Wiping_Intensity :> Integer;
  @VssSignalMetadata about Vehicle_Body_Windshield_Wiping_Intensity {
    path = "Vehicle.Body.Windshield.Wiping.Intensity";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Relative intensity/sensitivity for interval and rain sensor mode as requested by user/driver. Has no significance if Windshield.Wiping.Mode is OFF/SLOW/MEDIUM/FAST 0 - wipers inactive. 1 - minimum intensity (lowest frequency/sensitivity, longest interval). 2/3/4/... - higher intensity (higher frequency/sensitivity, shorter interval). Maximum value supported is vehicle specific.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Windshield_Wiping_IsWipersWorn :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Windshield_Wiping_IsWipersWorn {
    path = "Vehicle.Body.Windshield.Wiping.IsWipersWorn";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Wiper wear status. True = Worn, Replacement recommended or required. False = Not Worn.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Windshield_Wiping_Mode :> Vehicle_Body_Windshield_Wiping_Mode_AllowedValue;
  @VssSignalMetadata about Vehicle_Body_Windshield_Wiping_Mode {
    path = "Vehicle.Body.Windshield.Wiping.Mode";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Wiper mode requested by user/driver. INTERVAL indicates intermittent wiping, with fixed time interval between each wipe. RAIN_SENSOR indicates intermittent wiping based on rain intensity.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Body_Windshield_Wiping_Mode {
    allowedValues = "OFF, SLOW, MEDIUM, FAST, INTERVAL, RAIN_SENSOR";
  }

  attribute def Vehicle_Body_Windshield_Wiping_System_ActualPosition :> Real;
  @VssSignalMetadata about Vehicle_Body_Windshield_Wiping_System_ActualPosition {
    path = "Vehicle.Body.Windshield.Wiping.System.ActualPosition";
    kind = "actuator";
    datatype = "float";
    sourceDescription = "Actual position of main wiper blade for the wiper system relative to reference position. Location of reference position (0 degrees) and direction of positive/negative degrees is vehicle specific.";
    sourceComment = "Default parking position might be used as reference position.";
  }
  @VssQuantityMetadata about Vehicle_Body_Windshield_Wiping_System_ActualPosition {
    quantityReference = "ISQ::planeAngle";
    unitReference = "SI::degree";
  }

  attribute def Vehicle_Body_Windshield_Wiping_System_DriveCurrent :> Real;
  @VssSignalMetadata about Vehicle_Body_Windshield_Wiping_System_DriveCurrent {
    path = "Vehicle.Body.Windshield.Wiping.System.DriveCurrent";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Actual current used by wiper drive.";
    sourceComment = "May be negative in special situations.";
  }
  @VssQuantityMetadata about Vehicle_Body_Windshield_Wiping_System_DriveCurrent {
    quantityReference = "ISQ::electricCurrent";
    unitReference = "SI::ampere";
  }

  attribute def Vehicle_Body_Windshield_Wiping_System_Frequency :> Integer;
  @VssSignalMetadata about Vehicle_Body_Windshield_Wiping_System_Frequency {
    path = "Vehicle.Body.Windshield.Wiping.System.Frequency";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Wiping frequency/speed, measured in cycles per minute. The signal concerns the actual speed of the wiper blades when moving. Intervals/pauses are excluded, i.e. the value corresponds to the number of cycles that would be completed in 1 minute if wiping permanently over default range.";
    sourceComment = "Examples - 0 = Wipers stopped, 80 = Wipers doing 80 cycles per minute (in WIPE mode).";
  }
  @VssQuantityMetadata about Vehicle_Body_Windshield_Wiping_System_Frequency {
    quantityReference = "ISQ::frequency";
    unitReference = "SI-derived cycles/minute";
  }

  attribute def Vehicle_Body_Windshield_Wiping_System_IsBlocked :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Windshield_Wiping_System_IsBlocked {
    path = "Vehicle.Body.Windshield.Wiping.System.IsBlocked";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if wiper movement is blocked. True = Movement blocked. False = Movement not blocked.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Windshield_Wiping_System_IsEndingWipeCycle :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Windshield_Wiping_System_IsEndingWipeCycle {
    path = "Vehicle.Body.Windshield.Wiping.System.IsEndingWipeCycle";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if current wipe movement is completed or near completion. True = Movement is completed or near completion. Changes to RequestedPosition will be executed first after reaching previous RequestedPosition, if it has not already been reached. False = Movement is not near completion. Any change to RequestedPosition will be executed immediately. Change of direction may not be allowed.";
    sourceComment = "In continuous wiping between A and B this sensor can be used a trigger to update TargetPosition.";
  }

  attribute def Vehicle_Body_Windshield_Wiping_System_IsOverheated :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Windshield_Wiping_System_IsOverheated {
    path = "Vehicle.Body.Windshield.Wiping.System.IsOverheated";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if wiper system is overheated. True = Wiper system overheated. False = Wiper system not overheated.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Windshield_Wiping_System_IsPositionReached :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Windshield_Wiping_System_IsPositionReached {
    path = "Vehicle.Body.Windshield.Wiping.System.IsPositionReached";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if a requested position has been reached. IsPositionReached refers to the previous position in case the TargetPosition is updated while IsEndingWipeCycle=True. True = Current or Previous TargetPosition reached. False = Position not (yet) reached, or wipers have moved away from the reached position.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Windshield_Wiping_System_IsWiperError :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Windshield_Wiping_System_IsWiperError {
    path = "Vehicle.Body.Windshield.Wiping.System.IsWiperError";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates system failure. True if wiping is disabled due to system failure.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Windshield_Wiping_System_IsWiping :> Boolean;
  @VssSignalMetadata about Vehicle_Body_Windshield_Wiping_System_IsWiping {
    path = "Vehicle.Body.Windshield.Wiping.System.IsWiping";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates wiper movement. True if wiper blades are moving. Change of direction shall be considered as IsWiping if wipers will continue to move directly after the change of direction.";
    sourceComment = "";
  }

  attribute def Vehicle_Body_Windshield_Wiping_System_Mode :> Vehicle_Body_Windshield_Wiping_System_Mode_AllowedValue;
  @VssSignalMetadata about Vehicle_Body_Windshield_Wiping_System_Mode {
    path = "Vehicle.Body.Windshield.Wiping.System.Mode";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Requested mode of wiper system. STOP_HOLD means that the wipers shall move to position given by TargetPosition and then hold the position. WIPE means that wipers shall move to the position given by TargetPosition and then hold the position if no new TargetPosition is requested. PLANT_MODE means that wiping is disabled. Exact behavior is vehicle specific. EMERGENCY_STOP means that wiping shall be immediately stopped without holding the position.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Body_Windshield_Wiping_System_Mode {
    allowedValues = "STOP_HOLD, WIPE, PLANT_MODE, EMERGENCY_STOP";
  }

  attribute def Vehicle_Body_Windshield_Wiping_System_TargetPosition :> Real;
  @VssSignalMetadata about Vehicle_Body_Windshield_Wiping_System_TargetPosition {
    path = "Vehicle.Body.Windshield.Wiping.System.TargetPosition";
    kind = "actuator";
    datatype = "float";
    sourceDescription = "Requested position of main wiper blade for the wiper system relative to reference position. Location of reference position (0 degrees) and direction of positive/negative degrees is vehicle specific. System behavior when receiving TargetPosition depends on Mode and IsEndingWipeCycle. Supported values are vehicle specific and might be dynamically corrected. If IsEndingWipeCycle=True then wipers will complete current movement before actuating new TargetPosition. If IsEndingWipeCycle=False then wipers will directly change destination if the TargetPosition is changed.";
    sourceComment = "Default parking position might be used as reference position.";
  }
  @VssQuantityMetadata about Vehicle_Body_Windshield_Wiping_System_TargetPosition {
    quantityReference = "ISQ::planeAngle";
    unitReference = "SI::degree";
  }

  attribute def Vehicle_Body_Windshield_Wiping_WiperWear :> Integer;
  @VssSignalMetadata about Vehicle_Body_Windshield_Wiping_WiperWear {
    path = "Vehicle.Body.Windshield.Wiping.WiperWear";
    kind = "sensor";
    datatype = "uint8";
    sourceDescription = "Wiper wear as percent. 0 = No Wear. 100 = Worn. Replacement required. Method for calculating or estimating wiper wear is vehicle specific. For windshields with multiple wipers the wear reported shall correspond to the most worn wiper.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Body_Windshield_Wiping_WiperWear {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Body_Windshield_Wiping_WiperWear {
    minValue = "";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Convertible_Status :> Vehicle_Cabin_Convertible_Status_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Convertible_Status {
    path = "Vehicle.Cabin.Convertible.Status";
    kind = "sensor";
    datatype = "string";
    sourceDescription = "Roof status on convertible vehicles.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Convertible_Status {
    allowedValues = "UNDEFINED, CLOSED, OPEN, CLOSING, OPENING, STALLED";
  }

  attribute def Vehicle_Cabin_Door_IsChildLockActive :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Door_IsChildLockActive {
    path = "Vehicle.Cabin.Door.IsChildLockActive";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Is door child lock active. True = Door cannot be opened from inside. False = Door can be opened from inside.";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_Door_IsLocked :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Door_IsLocked {
    path = "Vehicle.Cabin.Door.IsLocked";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is item locked or unlocked. True = Locked. False = Unlocked.";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_Door_IsOpen :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Door_IsOpen {
    path = "Vehicle.Cabin.Door.IsOpen";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is item open or closed? True = Fully or partially open. False = Fully closed.";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_Door_Position :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_Door_Position {
    path = "Vehicle.Cabin.Door.Position";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Item position. 0 = Start position 100 = End position.";
    sourceComment = "Relationship between Open/Close and Start/End position is item dependent.";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Door_Position {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Door_Position {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Door_Shade_IsOpen :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Door_Shade_IsOpen {
    path = "Vehicle.Cabin.Door.Shade.IsOpen";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is item open or closed? True = Fully or partially open. False = Fully closed.";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_Door_Shade_Position :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_Door_Shade_Position {
    path = "Vehicle.Cabin.Door.Shade.Position";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Item position. 0 = Start position 100 = End position.";
    sourceComment = "Relationship between Open/Close and Start/End position is item dependent.";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Door_Shade_Position {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Door_Shade_Position {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Door_Shade_Switch :> Vehicle_Cabin_Door_Shade_Switch_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Door_Shade_Switch {
    path = "Vehicle.Cabin.Door.Shade.Switch";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Switch controlling sliding action such as window, sunroof, or blind.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Door_Shade_Switch {
    allowedValues = "INACTIVE, CLOSE, OPEN, ONE_SHOT_CLOSE, ONE_SHOT_OPEN";
  }

  attribute def Vehicle_Cabin_Door_Switch :> Vehicle_Cabin_Door_Switch_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Door_Switch {
    path = "Vehicle.Cabin.Door.Switch";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Switch controlling sliding action such as window, sunroof, or blind.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Door_Switch {
    allowedValues = "INACTIVE, CLOSE, OPEN, ONE_SHOT_CLOSE, ONE_SHOT_OPEN";
  }

  attribute def Vehicle_Cabin_Door_Window_IsOpen :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Door_Window_IsOpen {
    path = "Vehicle.Cabin.Door.Window.IsOpen";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is item open or closed? True = Fully or partially open. False = Fully closed.";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_Door_Window_Position :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_Door_Window_Position {
    path = "Vehicle.Cabin.Door.Window.Position";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Item position. 0 = Start position 100 = End position.";
    sourceComment = "Relationship between Open/Close and Start/End position is item dependent.";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Door_Window_Position {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Door_Window_Position {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Door_Window_Switch :> Vehicle_Cabin_Door_Window_Switch_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Door_Window_Switch {
    path = "Vehicle.Cabin.Door.Window.Switch";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Switch controlling sliding action such as window, sunroof, or blind.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Door_Window_Switch {
    allowedValues = "INACTIVE, CLOSE, OPEN, ONE_SHOT_CLOSE, ONE_SHOT_OPEN";
  }

  attribute def Vehicle_Cabin_DoorCount :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_DoorCount {
    path = "Vehicle.Cabin.DoorCount";
    kind = "attribute";
    datatype = "uint8";
    sourceDescription = "Number of doors in vehicle.";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_DriverPosition :> Vehicle_Cabin_DriverPosition_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_DriverPosition {
    path = "Vehicle.Cabin.DriverPosition";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "The position of the driver seat in row 1.";
    sourceComment = "Some signals use DriverSide and PassengerSide as instances. If this signal specifies that DriverPosition is LEFT or MIDDLE, then DriverSide refers to left side and PassengerSide to right side. If this signal specifies that DriverPosition is RIGHT, then DriverSide refers to right side and PassengerSide to left side.";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_DriverPosition {
    allowedValues = "LEFT, MIDDLE, RIGHT";
  }

  attribute def Vehicle_Cabin_HVAC_AmbientAirTemperature :> Real;
  @VssSignalMetadata about Vehicle_Cabin_HVAC_AmbientAirTemperature {
    path = "Vehicle.Cabin.HVAC.AmbientAirTemperature";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Ambient air temperature inside the vehicle.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_HVAC_AmbientAirTemperature {
    quantityReference = "ISQ::thermodynamicTemperature";
    unitReference = "SI::degreeCelsius";
  }

  attribute def Vehicle_Cabin_HVAC_IsAirConditioningActive :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_HVAC_IsAirConditioningActive {
    path = "Vehicle.Cabin.HVAC.IsAirConditioningActive";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is Air conditioning active.";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_HVAC_IsAutoPowerOptimize :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_HVAC_IsAutoPowerOptimize {
    path = "Vehicle.Cabin.HVAC.IsAutoPowerOptimize";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Auto Power Optimization Flag When set to 'true', the system enables automatic power optimization, dynamically adjusting the power optimization level based on runtime conditions or features managed by the OEM. When set to 'false', manual control of the power optimization level is allowed.";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_HVAC_IsFrontDefrosterActive :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_HVAC_IsFrontDefrosterActive {
    path = "Vehicle.Cabin.HVAC.IsFrontDefrosterActive";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is front defroster active.";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_HVAC_IsRearDefrosterActive :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_HVAC_IsRearDefrosterActive {
    path = "Vehicle.Cabin.HVAC.IsRearDefrosterActive";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is rear defroster active.";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_HVAC_IsRecirculationActive :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_HVAC_IsRecirculationActive {
    path = "Vehicle.Cabin.HVAC.IsRecirculationActive";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is recirculation active.";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_HVAC_PowerOptimizeLevel :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_HVAC_PowerOptimizeLevel {
    path = "Vehicle.Cabin.HVAC.PowerOptimizeLevel";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Power optimization level for this branch/subsystem. A higher number indicates more aggressive power optimization. Level 0 indicates that all functionality is enabled, no power optimization enabled. Level 10 indicates most aggressive power optimization mode, only essential functionality enabled.";
    sourceComment = "";
  }
  @VssRangeMetadata about Vehicle_Cabin_HVAC_PowerOptimizeLevel {
    minValue = "0";
    maxValue = "10";
  }

  attribute def Vehicle_Cabin_HVAC_Station_AirDistribution :> Vehicle_Cabin_HVAC_Station_AirDistribution_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_HVAC_Station_AirDistribution {
    path = "Vehicle.Cabin.HVAC.Station.AirDistribution";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Direction of airstream";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_HVAC_Station_AirDistribution {
    allowedValues = "UP, MIDDLE, DOWN";
  }

  attribute def Vehicle_Cabin_HVAC_Station_FanSpeed :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_HVAC_Station_FanSpeed {
    path = "Vehicle.Cabin.HVAC.Station.FanSpeed";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Fan Speed, 0 = off. 100 = max";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_HVAC_Station_FanSpeed {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_HVAC_Station_FanSpeed {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_HVAC_Station_Temperature :> Real;
  @VssSignalMetadata about Vehicle_Cabin_HVAC_Station_Temperature {
    path = "Vehicle.Cabin.HVAC.Station.Temperature";
    kind = "actuator";
    datatype = "float";
    sourceDescription = "Temperature";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_HVAC_Station_Temperature {
    quantityReference = "ISQ::thermodynamicTemperature";
    unitReference = "SI::degreeCelsius";
  }

  attribute def Vehicle_Cabin_Infotainment_HMI_Brightness :> Real;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_HMI_Brightness {
    path = "Vehicle.Cabin.Infotainment.HMI.Brightness";
    kind = "actuator";
    datatype = "float";
    sourceDescription = "Brightness of the HMI, relative to supported range. 0 = Lowest brightness possible. 100 = Maximum Brightness possible.";
    sourceComment = "The value 0 does not necessarily correspond to a turned off HMI, as it may not be allowed/supported to turn off the HMI completely.";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Infotainment_HMI_Brightness {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Infotainment_HMI_Brightness {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Infotainment_HMI_CurrentLanguage :> String;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_HMI_CurrentLanguage {
    path = "Vehicle.Cabin.Infotainment.HMI.CurrentLanguage";
    kind = "sensor";
    datatype = "string";
    sourceDescription = "ISO 639-1 standard language code for the current HMI";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_Infotainment_HMI_DateFormat :> Vehicle_Cabin_Infotainment_HMI_DateFormat_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_HMI_DateFormat {
    path = "Vehicle.Cabin.Infotainment.HMI.DateFormat";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Date format used in the current HMI";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Infotainment_HMI_DateFormat {
    allowedValues = "YYYY_MM_DD, DD_MM_YYYY, MM_DD_YYYY, YY_MM_DD, DD_MM_YY, MM_DD_YY";
  }

  attribute def Vehicle_Cabin_Infotainment_HMI_DayNightMode :> Vehicle_Cabin_Infotainment_HMI_DayNightMode_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_HMI_DayNightMode {
    path = "Vehicle.Cabin.Infotainment.HMI.DayNightMode";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Current display theme";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Infotainment_HMI_DayNightMode {
    allowedValues = "DAY, NIGHT";
  }

  attribute def Vehicle_Cabin_Infotainment_HMI_DisplayOffDuration :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_HMI_DisplayOffDuration {
    path = "Vehicle.Cabin.Infotainment.HMI.DisplayOffDuration";
    kind = "actuator";
    datatype = "uint16";
    sourceDescription = "Duration in seconds before the display is turned off. Value shall be 0 if screen never shall turn off.";
    sourceComment = "Display shall be turned off at HMI.LastActionTime + HMI.DisplayOffDuration, unless HMI.IsScreenAlwaysOn==True.";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Infotainment_HMI_DisplayOffDuration {
    quantityReference = "ISQ::time";
    unitReference = "SI::second";
  }

  attribute def Vehicle_Cabin_Infotainment_HMI_DistanceUnit :> Vehicle_Cabin_Infotainment_HMI_DistanceUnit_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_HMI_DistanceUnit {
    path = "Vehicle.Cabin.Infotainment.HMI.DistanceUnit";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Distance unit used in the current HMI";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Infotainment_HMI_DistanceUnit {
    allowedValues = "MILES, KILOMETERS";
  }

  attribute def Vehicle_Cabin_Infotainment_HMI_EVEconomyUnits :> Vehicle_Cabin_Infotainment_HMI_EVEconomyUnits_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_HMI_EVEconomyUnits {
    path = "Vehicle.Cabin.Infotainment.HMI.EVEconomyUnits";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "EV fuel economy unit used in the current HMI";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Infotainment_HMI_EVEconomyUnits {
    allowedValues = "MILES_PER_KILOWATT_HOUR, KILOMETERS_PER_KILOWATT_HOUR, KILOWATT_HOURS_PER_100_MILES, KILOWATT_HOURS_PER_100_KILOMETERS, WATT_HOURS_PER_MILE, WATT_HOURS_PER_KILOMETER";
  }

  attribute def Vehicle_Cabin_Infotainment_HMI_EVEnergyUnits :> Vehicle_Cabin_Infotainment_HMI_EVEnergyUnits_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_HMI_EVEnergyUnits {
    path = "Vehicle.Cabin.Infotainment.HMI.EVEnergyUnits";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "EV energy unit used in the current HMI";
    sourceComment = "Ampere hours is by definition not an energy unit, but can be used as a measurement of energy if the voltage, like nominal voltage of the battery, is known.";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Infotainment_HMI_EVEnergyUnits {
    allowedValues = "WATT_HOURS, AMPERE_HOURS, KILOWATT_HOURS";
  }

  attribute def Vehicle_Cabin_Infotainment_HMI_FontSize :> Vehicle_Cabin_Infotainment_HMI_FontSize_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_HMI_FontSize {
    path = "Vehicle.Cabin.Infotainment.HMI.FontSize";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Font size used in the current HMI";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Infotainment_HMI_FontSize {
    allowedValues = "STANDARD, LARGE, EXTRA_LARGE";
  }

  attribute def Vehicle_Cabin_Infotainment_HMI_FuelEconomyUnits :> Vehicle_Cabin_Infotainment_HMI_FuelEconomyUnits_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_HMI_FuelEconomyUnits {
    path = "Vehicle.Cabin.Infotainment.HMI.FuelEconomyUnits";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Fuel economy unit used in the current HMI";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Infotainment_HMI_FuelEconomyUnits {
    allowedValues = "MPG_UK, MPG_US, MILES_PER_LITER, KILOMETERS_PER_LITER, LITERS_PER_100_KILOMETERS";
  }

  attribute def Vehicle_Cabin_Infotainment_HMI_FuelVolumeUnit :> Vehicle_Cabin_Infotainment_HMI_FuelVolumeUnit_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_HMI_FuelVolumeUnit {
    path = "Vehicle.Cabin.Infotainment.HMI.FuelVolumeUnit";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Fuel volume unit used in the current HMI";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Infotainment_HMI_FuelVolumeUnit {
    allowedValues = "LITER, GALLON_US, GALLON_UK";
  }

  attribute def Vehicle_Cabin_Infotainment_HMI_IsScreenAlwaysOn :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_HMI_IsScreenAlwaysOn {
    path = "Vehicle.Cabin.Infotainment.HMI.IsScreenAlwaysOn";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Used to prevent the screen going black if no action placed.";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_Infotainment_HMI_LastActionTime :> String;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_HMI_LastActionTime {
    path = "Vehicle.Cabin.Infotainment.HMI.LastActionTime";
    kind = "sensor";
    datatype = "string";
    sourceDescription = "Time for last hmi action, formatted according to ISO 8601 with UTC time zone.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Infotainment_HMI_LastActionTime {
    quantityReference = "n/a";
    unitReference = "ISO 8601 lexical date/time string";
  }

  attribute def Vehicle_Cabin_Infotainment_HMI_SpeedUnit :> Vehicle_Cabin_Infotainment_HMI_SpeedUnit_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_HMI_SpeedUnit {
    path = "Vehicle.Cabin.Infotainment.HMI.SpeedUnit";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Speed unit used in the current HMI";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Infotainment_HMI_SpeedUnit {
    allowedValues = "METERS_PER_SECOND, MILES_PER_HOUR, KILOMETERS_PER_HOUR";
  }

  attribute def Vehicle_Cabin_Infotainment_HMI_TemperatureUnit :> Vehicle_Cabin_Infotainment_HMI_TemperatureUnit_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_HMI_TemperatureUnit {
    path = "Vehicle.Cabin.Infotainment.HMI.TemperatureUnit";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Temperature unit used in the current HMI";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Infotainment_HMI_TemperatureUnit {
    allowedValues = "C, F";
  }

  attribute def Vehicle_Cabin_Infotainment_HMI_TimeFormat :> Vehicle_Cabin_Infotainment_HMI_TimeFormat_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_HMI_TimeFormat {
    path = "Vehicle.Cabin.Infotainment.HMI.TimeFormat";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Time format used in the current HMI";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Infotainment_HMI_TimeFormat {
    allowedValues = "HR_12, HR_24";
  }

  attribute def Vehicle_Cabin_Infotainment_HMI_TirePressureUnit :> Vehicle_Cabin_Infotainment_HMI_TirePressureUnit_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_HMI_TirePressureUnit {
    path = "Vehicle.Cabin.Infotainment.HMI.TirePressureUnit";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Tire pressure unit used in the current HMI";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Infotainment_HMI_TirePressureUnit {
    allowedValues = "PSI, KPA, BAR";
  }

  attribute def Vehicle_Cabin_Infotainment_IsAutoPowerOptimize :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_IsAutoPowerOptimize {
    path = "Vehicle.Cabin.Infotainment.IsAutoPowerOptimize";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Auto Power Optimization Flag When set to 'true', the system enables automatic power optimization, dynamically adjusting the power optimization level based on runtime conditions or features managed by the OEM. When set to 'false', manual control of the power optimization level is allowed.";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_Infotainment_Media_Action :> Vehicle_Cabin_Infotainment_Media_Action_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_Media_Action {
    path = "Vehicle.Cabin.Infotainment.Media.Action";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Tells if the media was";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Infotainment_Media_Action {
    allowedValues = "UNKNOWN, STOP, PLAY, FAST_FORWARD, FAST_BACKWARD, SKIP_FORWARD, SKIP_BACKWARD";
  }

  attribute def Vehicle_Cabin_Infotainment_Media_DeclinedURI :> String;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_Media_DeclinedURI {
    path = "Vehicle.Cabin.Infotainment.Media.DeclinedURI";
    kind = "sensor";
    datatype = "string";
    sourceDescription = "URI of suggested media that was declined";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_Infotainment_Media_Played_Album :> String;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_Media_Played_Album {
    path = "Vehicle.Cabin.Infotainment.Media.Played.Album";
    kind = "sensor";
    datatype = "string";
    sourceDescription = "Name of album being played";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_Infotainment_Media_Played_Artist :> String;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_Media_Played_Artist {
    path = "Vehicle.Cabin.Infotainment.Media.Played.Artist";
    kind = "sensor";
    datatype = "string";
    sourceDescription = "Name of artist being played";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_Infotainment_Media_Played_Genre :> String;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_Media_Played_Genre {
    path = "Vehicle.Cabin.Infotainment.Media.Played.Genre";
    kind = "sensor";
    datatype = "string";
    sourceDescription = "Name of genre being played";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_Infotainment_Media_Played_PlaybackRate :> Real;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_Media_Played_PlaybackRate {
    path = "Vehicle.Cabin.Infotainment.Media.Played.PlaybackRate";
    kind = "actuator";
    datatype = "float";
    sourceDescription = "Current playback rate of media being played.";
    sourceComment = "The normal playback rate is multiplied by this value to obtain the current rate, so a value of 1.0 indicates normal speed. Values of lower than 1.0 make the media play slower than normal. Values of higher than 1.0 make the media play faster than normal.";
  }

  attribute def Vehicle_Cabin_Infotainment_Media_Played_Source :> Vehicle_Cabin_Infotainment_Media_Played_Source_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_Media_Played_Source {
    path = "Vehicle.Cabin.Infotainment.Media.Played.Source";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Media selected for playback";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Infotainment_Media_Played_Source {
    allowedValues = "UNKNOWN, SIRIUS_XM, AM, FM, DAB, TV, CD, DVD, AUX, USB, DISK, BLUETOOTH, INTERNET, VOICE, BEEP";
  }

  attribute def Vehicle_Cabin_Infotainment_Media_Played_Track :> String;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_Media_Played_Track {
    path = "Vehicle.Cabin.Infotainment.Media.Played.Track";
    kind = "sensor";
    datatype = "string";
    sourceDescription = "Name of track being played";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_Infotainment_Media_Played_URI :> String;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_Media_Played_URI {
    path = "Vehicle.Cabin.Infotainment.Media.Played.URI";
    kind = "sensor";
    datatype = "string";
    sourceDescription = "User Resource associated with the media";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_Infotainment_Media_SelectedURI :> String;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_Media_SelectedURI {
    path = "Vehicle.Cabin.Infotainment.Media.SelectedURI";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "URI of suggested media that was selected";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_Infotainment_Media_Volume :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_Media_Volume {
    path = "Vehicle.Cabin.Infotainment.Media.Volume";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Current Media Volume";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Infotainment_Media_Volume {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Infotainment_Media_Volume {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Infotainment_Navigation_DestinationSet_Latitude :> Real;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_Navigation_DestinationSet_Latitude {
    path = "Vehicle.Cabin.Infotainment.Navigation.DestinationSet.Latitude";
    kind = "actuator";
    datatype = "double";
    sourceDescription = "Latitude of destination in WGS 84 geodetic coordinates.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Infotainment_Navigation_DestinationSet_Latitude {
    quantityReference = "ISQ::planeAngle";
    unitReference = "SI::degree";
  }
  @VssRangeMetadata about Vehicle_Cabin_Infotainment_Navigation_DestinationSet_Latitude {
    minValue = "-90";
    maxValue = "90";
  }

  attribute def Vehicle_Cabin_Infotainment_Navigation_DestinationSet_Longitude :> Real;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_Navigation_DestinationSet_Longitude {
    path = "Vehicle.Cabin.Infotainment.Navigation.DestinationSet.Longitude";
    kind = "actuator";
    datatype = "double";
    sourceDescription = "Longitude of destination in WGS 84 geodetic coordinates.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Infotainment_Navigation_DestinationSet_Longitude {
    quantityReference = "ISQ::planeAngle";
    unitReference = "SI::degree";
  }
  @VssRangeMetadata about Vehicle_Cabin_Infotainment_Navigation_DestinationSet_Longitude {
    minValue = "-180";
    maxValue = "180";
  }

  attribute def Vehicle_Cabin_Infotainment_Navigation_GuidanceVoice :> Vehicle_Cabin_Infotainment_Navigation_GuidanceVoice_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_Navigation_GuidanceVoice {
    path = "Vehicle.Cabin.Infotainment.Navigation.GuidanceVoice";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Navigation guidance state that was selected.";
    sourceComment = "ETC indicates a voice alternative not covered by the explicitly listed alternatives.";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Infotainment_Navigation_GuidanceVoice {
    allowedValues = "STANDARD_MALE, STANDARD_FEMALE, ETC";
  }

  attribute def Vehicle_Cabin_Infotainment_Navigation_Map_IsAutoScaleModeUsed :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_Navigation_Map_IsAutoScaleModeUsed {
    path = "Vehicle.Cabin.Infotainment.Navigation.Map.IsAutoScaleModeUsed";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Used to select auto-scaling mode. This feature dynamically adjusts the zoom level of the map to provide an optimal view based on the current speed of the vehicle";
    sourceComment = "If true, then auto-scaling mode is used. If false, then manual-scaling mode is used.";
  }

  attribute def Vehicle_Cabin_Infotainment_Navigation_Mute :> Vehicle_Cabin_Infotainment_Navigation_Mute_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_Navigation_Mute {
    path = "Vehicle.Cabin.Infotainment.Navigation.Mute";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Navigation mute state that was selected.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Infotainment_Navigation_Mute {
    allowedValues = "MUTED, ALERT_ONLY, UNMUTED";
  }

  attribute def Vehicle_Cabin_Infotainment_Navigation_Volume :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_Navigation_Volume {
    path = "Vehicle.Cabin.Infotainment.Navigation.Volume";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Current navigation volume";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Infotainment_Navigation_Volume {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Infotainment_Navigation_Volume {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Infotainment_PowerOptimizeLevel :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_PowerOptimizeLevel {
    path = "Vehicle.Cabin.Infotainment.PowerOptimizeLevel";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Power optimization level for this branch/subsystem. A higher number indicates more aggressive power optimization. Level 0 indicates that all functionality is enabled, no power optimization enabled. Level 10 indicates most aggressive power optimization mode, only essential functionality enabled.";
    sourceComment = "";
  }
  @VssRangeMetadata about Vehicle_Cabin_Infotainment_PowerOptimizeLevel {
    minValue = "0";
    maxValue = "10";
  }

  attribute def Vehicle_Cabin_Infotainment_SmartphoneProjection_Active :> Vehicle_Cabin_Infotainment_SmartphoneProjection_Active_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_SmartphoneProjection_Active {
    path = "Vehicle.Cabin.Infotainment.SmartphoneProjection.Active";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Projection activation info.";
    sourceComment = "NONE indicates that projection is not supported.";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Infotainment_SmartphoneProjection_Active {
    allowedValues = "NONE, ACTIVE, INACTIVE";
  }

  attribute def Vehicle_Cabin_Infotainment_SmartphoneProjection_Source :> Vehicle_Cabin_Infotainment_SmartphoneProjection_Source_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_SmartphoneProjection_Source {
    path = "Vehicle.Cabin.Infotainment.SmartphoneProjection.Source";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Connectivity source selected for projection.";
    sourceComment = "Smartphone projection exposes or controls specific applications on the Smartphone on the vehicle infotainment system.";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Infotainment_SmartphoneProjection_Source {
    allowedValues = "USB, BLUETOOTH, WIFI";
  }

  attribute def Vehicle_Cabin_Infotainment_SmartphoneProjection_SupportedMode :> Vehicle_Cabin_Infotainment_SmartphoneProjection_SupportedMode_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_SmartphoneProjection_SupportedMode {
    path = "Vehicle.Cabin.Infotainment.SmartphoneProjection.SupportedMode";
    kind = "attribute";
    datatype = "string[]";
    sourceDescription = "Supportable list for projection.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Infotainment_SmartphoneProjection_SupportedMode {
    allowedValues = "ANDROID_AUTO, APPLE_CARPLAY, MIRROR_LINK, OTHER";
  }

  attribute def Vehicle_Cabin_Infotainment_SmartphoneScreenMirroring_Active :> Vehicle_Cabin_Infotainment_SmartphoneScreenMirroring_Active_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_SmartphoneScreenMirroring_Active {
    path = "Vehicle.Cabin.Infotainment.SmartphoneScreenMirroring.Active";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Mirroring activation info.";
    sourceComment = "NONE indicates that mirroring is not supported.";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Infotainment_SmartphoneScreenMirroring_Active {
    allowedValues = "NONE, ACTIVE, INACTIVE";
  }

  attribute def Vehicle_Cabin_Infotainment_SmartphoneScreenMirroring_Source :> Vehicle_Cabin_Infotainment_SmartphoneScreenMirroring_Source_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Infotainment_SmartphoneScreenMirroring_Source {
    path = "Vehicle.Cabin.Infotainment.SmartphoneScreenMirroring.Source";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Connectivity source selected for mirroring.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Infotainment_SmartphoneScreenMirroring_Source {
    allowedValues = "USB, BLUETOOTH, WIFI";
  }

  attribute def Vehicle_Cabin_IsAutoPowerOptimize :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_IsAutoPowerOptimize {
    path = "Vehicle.Cabin.IsAutoPowerOptimize";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Auto Power Optimization Flag When set to 'true', the system enables automatic power optimization, dynamically adjusting the power optimization level based on runtime conditions or features managed by the OEM. When set to 'false', manual control of the power optimization level is allowed.";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_IsWindowChildLockEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_IsWindowChildLockEngaged {
    path = "Vehicle.Cabin.IsWindowChildLockEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is window child lock engaged. True = Engaged. False = Disengaged.";
    sourceComment = "Window child lock refers to the functionality to disable the move window button next to most windows, so that they only can be operated by the driver.";
  }

  attribute def Vehicle_Cabin_Light_AmbientLight_Color :> String;
  @VssSignalMetadata about Vehicle_Cabin_Light_AmbientLight_Color {
    path = "Vehicle.Cabin.Light.AmbientLight.Color";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Hexadecimal color code represented as a 3-byte RGB (i.e. Red, Green, and Blue) value preceded by a hash symbol \"#\". Allowed range \"#000000\" to \"#FFFFFF\".";
    sourceComment = "For example; \"#C0C0C0\" = Silver, \"#FFD700\" = Gold, \"#000000\" = Black, \"#FFFFFF\" = White, etc.";
  }

  attribute def Vehicle_Cabin_Light_AmbientLight_Intensity :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_Light_AmbientLight_Intensity {
    path = "Vehicle.Cabin.Light.AmbientLight.Intensity";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "How much of the maximum possible brightness of the light is used. 1 = Maximum attenuation, 100 = No attenuation (i.e. full brightness).";
    sourceComment = "Minimum value cannot be zero as on/off is controlled by the actuator IsLightOn. V4.0 moved from Cabin.Lights.AmbientLight.Intensity to enable individual control of lights via the SingleConfigurableLight.vspec.";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Light_AmbientLight_Intensity {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Light_AmbientLight_Intensity {
    minValue = "1";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Light_AmbientLight_IsLightOn :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Light_AmbientLight_IsLightOn {
    path = "Vehicle.Cabin.Light.AmbientLight.IsLightOn";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Indicates whether the light is turned on. True = On, False = Off.";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_Light_InteractiveLightBar_Color :> String;
  @VssSignalMetadata about Vehicle_Cabin_Light_InteractiveLightBar_Color {
    path = "Vehicle.Cabin.Light.InteractiveLightBar.Color";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Hexadecimal color code represented as a 3-byte RGB (i.e. Red, Green, and Blue) value preceded by a hash symbol \"#\". Allowed range \"#000000\" to \"#FFFFFF\".";
    sourceComment = "For example; \"#C0C0C0\" = Silver, \"#FFD700\" = Gold, \"#000000\" = Black, \"#FFFFFF\" = White, etc.";
  }

  attribute def Vehicle_Cabin_Light_InteractiveLightBar_Effect :> String;
  @VssSignalMetadata about Vehicle_Cabin_Light_InteractiveLightBar_Effect {
    path = "Vehicle.Cabin.Light.InteractiveLightBar.Effect";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Light effect selection from a predefined set of allowed values.";
    sourceComment = "Default and allowed values are OEM-specific and should be defined accordingly (e.g. with the use of overlays).";
  }

  attribute def Vehicle_Cabin_Light_InteractiveLightBar_Intensity :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_Light_InteractiveLightBar_Intensity {
    path = "Vehicle.Cabin.Light.InteractiveLightBar.Intensity";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "How much of the maximum possible brightness of the light is used. 1 = Maximum attenuation, 100 = No attenuation (i.e. full brightness).";
    sourceComment = "Minimum value cannot be zero as on/off is controlled by the actuator IsLightOn. V4.0 moved from Cabin.Lights.AmbientLight.Intensity to enable individual control of lights via the SingleConfigurableLight.vspec.";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Light_InteractiveLightBar_Intensity {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Light_InteractiveLightBar_Intensity {
    minValue = "1";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Light_InteractiveLightBar_IsLightOn :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Light_InteractiveLightBar_IsLightOn {
    path = "Vehicle.Cabin.Light.InteractiveLightBar.IsLightOn";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Indicates whether the light is turned on. True = On, False = Off.";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_Light_IsDomeOn :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Light_IsDomeOn {
    path = "Vehicle.Cabin.Light.IsDomeOn";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is central dome light on";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_Light_IsGloveBoxOn :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Light_IsGloveBoxOn {
    path = "Vehicle.Cabin.Light.IsGloveBoxOn";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is glove box light on";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_Light_PerceivedAmbientLight :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_Light_PerceivedAmbientLight {
    path = "Vehicle.Cabin.Light.PerceivedAmbientLight";
    kind = "sensor";
    datatype = "uint8";
    sourceDescription = "The percentage of ambient light that is measured (e.g., by a sensor) inside the cabin. 0 = No ambient light. 100 = Full brightness.";
    sourceComment = "V4.0 named changed from \"AmbientLight\" to \"PerceivedAmbientLight\". This is a read-only property that refers to the pre-existing light (e.g., natural light). If you are looking for the in-cabin decorative lights that sometimes are also called \"AmbientLights\", please refer to the branch Vehicle.Cabin.Light.AmbientLight.";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Light_PerceivedAmbientLight {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Light_PerceivedAmbientLight {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Light_Spotlight_Color :> String;
  @VssSignalMetadata about Vehicle_Cabin_Light_Spotlight_Color {
    path = "Vehicle.Cabin.Light.Spotlight.Color";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Hexadecimal color code represented as a 3-byte RGB (i.e. Red, Green, and Blue) value preceded by a hash symbol \"#\". Allowed range \"#000000\" to \"#FFFFFF\".";
    sourceComment = "For example; \"#C0C0C0\" = Silver, \"#FFD700\" = Gold, \"#000000\" = Black, \"#FFFFFF\" = White, etc.";
  }

  attribute def Vehicle_Cabin_Light_Spotlight_Intensity :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_Light_Spotlight_Intensity {
    path = "Vehicle.Cabin.Light.Spotlight.Intensity";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "How much of the maximum possible brightness of the light is used. 1 = Maximum attenuation, 100 = No attenuation (i.e. full brightness).";
    sourceComment = "Minimum value cannot be zero as on/off is controlled by the actuator IsLightOn. V4.0 moved from Cabin.Lights.AmbientLight.Intensity to enable individual control of lights via the SingleConfigurableLight.vspec.";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Light_Spotlight_Intensity {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Light_Spotlight_Intensity {
    minValue = "1";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Light_Spotlight_IsLightOn :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Light_Spotlight_IsLightOn {
    path = "Vehicle.Cabin.Light.Spotlight.IsLightOn";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Indicates whether the light is turned on. True = On, False = Off.";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_PowerOptimizeLevel :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_PowerOptimizeLevel {
    path = "Vehicle.Cabin.PowerOptimizeLevel";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Power optimization level for this branch/subsystem. A higher number indicates more aggressive power optimization. Level 0 indicates that all functionality is enabled, no power optimization enabled. Level 10 indicates most aggressive power optimization mode, only essential functionality enabled.";
    sourceComment = "";
  }
  @VssRangeMetadata about Vehicle_Cabin_PowerOptimizeLevel {
    minValue = "0";
    maxValue = "10";
  }

  attribute def Vehicle_Cabin_RearShade_IsOpen :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_RearShade_IsOpen {
    path = "Vehicle.Cabin.RearShade.IsOpen";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is item open or closed? True = Fully or partially open. False = Fully closed.";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_RearShade_Position :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_RearShade_Position {
    path = "Vehicle.Cabin.RearShade.Position";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Item position. 0 = Start position 100 = End position.";
    sourceComment = "Relationship between Open/Close and Start/End position is item dependent.";
  }
  @VssQuantityMetadata about Vehicle_Cabin_RearShade_Position {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_RearShade_Position {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_RearShade_Switch :> Vehicle_Cabin_RearShade_Switch_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_RearShade_Switch {
    path = "Vehicle.Cabin.RearShade.Switch";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Switch controlling sliding action such as window, sunroof, or blind.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_RearShade_Switch {
    allowedValues = "INACTIVE, CLOSE, OPEN, ONE_SHOT_CLOSE, ONE_SHOT_OPEN";
  }

  attribute def Vehicle_Cabin_RearviewMirror_DimmingLevel :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_RearviewMirror_DimmingLevel {
    path = "Vehicle.Cabin.RearviewMirror.DimmingLevel";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Dimming level of rear-view mirror. 0 = Undimmed. 100 = Fully dimmed.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_RearviewMirror_DimmingLevel {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_RearviewMirror_DimmingLevel {
    minValue = "";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Seat_Airbag_IsDeployed :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Airbag_IsDeployed {
    path = "Vehicle.Cabin.Seat.Airbag.IsDeployed";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Airbag deployment status. True = Airbag deployed. False = Airbag not deployed.";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_Seat_Airbag_IsEnabled :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Airbag_IsEnabled {
    path = "Vehicle.Cabin.Seat.Airbag.IsEnabled";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Airbag enabled status. True = Airbag enabled. False = Airbag not enabled.";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_Seat_Backrest_BottomLumbarSupport :> Real;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Backrest_BottomLumbarSupport {
    path = "Vehicle.Cabin.Seat.Backrest.BottomLumbarSupport";
    kind = "actuator";
    datatype = "float";
    sourceDescription = "Bottom lumbar support (in/out position). 0 = Innermost position. 100 = Outermost position.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Seat_Backrest_BottomLumbarSupport {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Seat_Backrest_BottomLumbarSupport {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Seat_Backrest_HeatingCooling :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Backrest_HeatingCooling {
    path = "Vehicle.Cabin.Seat.Backrest.HeatingCooling";
    kind = "actuator";
    datatype = "int8";
    sourceDescription = "Heating or Cooling requsted for the Item. -100 = Maximum cooling, 0 = Heating/cooling deactivated, 100 = Maximum heating.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Seat_Backrest_HeatingCooling {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Seat_Backrest_HeatingCooling {
    minValue = "-100";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Seat_Backrest_IsLessLumbarSupportSwitchEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Backrest_IsLessLumbarSupportSwitchEngaged {
    path = "Vehicle.Cabin.Seat.Backrest.IsLessLumbarSupportSwitchEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is switch for less lumbar support engaged.";
    sourceComment = "Affects the property (Backrest.LumbarSupport).";
  }

  attribute def Vehicle_Cabin_Seat_Backrest_IsLessSideBolsterSupportSwitchEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Backrest_IsLessSideBolsterSupportSwitchEngaged {
    path = "Vehicle.Cabin.Seat.Backrest.IsLessSideBolsterSupportSwitchEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is switch for less side bolster support engaged.";
    sourceComment = "Affects the property (Backrest.SideBolsterSupport).";
  }

  attribute def Vehicle_Cabin_Seat_Backrest_IsLumbarDownSwitchEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Backrest_IsLumbarDownSwitchEngaged {
    path = "Vehicle.Cabin.Seat.Backrest.IsLumbarDownSwitchEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Lumbar down switch engaged.";
    sourceComment = "Affects the property (Backrest.LumbarSupport).";
  }

  attribute def Vehicle_Cabin_Seat_Backrest_IsLumbarUpSwitchEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Backrest_IsLumbarUpSwitchEngaged {
    path = "Vehicle.Cabin.Seat.Backrest.IsLumbarUpSwitchEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Lumbar up switch engaged.";
    sourceComment = "Affects the property (Backrest.LumbarSupport).";
  }

  attribute def Vehicle_Cabin_Seat_Backrest_IsMoreLumbarSupportSwitchEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Backrest_IsMoreLumbarSupportSwitchEngaged {
    path = "Vehicle.Cabin.Seat.Backrest.IsMoreLumbarSupportSwitchEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is switch for more lumbar support engaged.";
    sourceComment = "Affects the property (Backrest.LumbarSupport).";
  }

  attribute def Vehicle_Cabin_Seat_Backrest_IsMoreSideBolsterSupportSwitchEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Backrest_IsMoreSideBolsterSupportSwitchEngaged {
    path = "Vehicle.Cabin.Seat.Backrest.IsMoreSideBolsterSupportSwitchEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is switch for more side bolster support engaged.";
    sourceComment = "Affects the property (Backrest.SideBolsterSupport).";
  }

  attribute def Vehicle_Cabin_Seat_Backrest_IsReclineBackwardSwitchEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Backrest_IsReclineBackwardSwitchEngaged {
    path = "Vehicle.Cabin.Seat.Backrest.IsReclineBackwardSwitchEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Backrest recline backward switch engaged.";
    sourceComment = "Affects the property (Backrest.Recline).";
  }

  attribute def Vehicle_Cabin_Seat_Backrest_IsReclineForwardSwitchEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Backrest_IsReclineForwardSwitchEngaged {
    path = "Vehicle.Cabin.Seat.Backrest.IsReclineForwardSwitchEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Backrest recline forward switch engaged.";
    sourceComment = "Affects the property (Backrest.Recline).";
  }

  attribute def Vehicle_Cabin_Seat_Backrest_LumbarHeight :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Backrest_LumbarHeight {
    path = "Vehicle.Cabin.Seat.Backrest.LumbarHeight";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Height of lumbar support. Position is relative within available movable range of the lumbar support. 0 = Lowermost position supported.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Seat_Backrest_LumbarHeight {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }
  @VssRangeMetadata about Vehicle_Cabin_Seat_Backrest_LumbarHeight {
    minValue = "0";
    maxValue = "";
  }

  attribute def Vehicle_Cabin_Seat_Backrest_LumbarSupport :> Real;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Backrest_LumbarSupport {
    path = "Vehicle.Cabin.Seat.Backrest.LumbarSupport";
    kind = "actuator";
    datatype = "float";
    sourceDescription = "Lumbar support (in/out position). 0 = Innermost position. 100 = Outermost position.";
    sourceComment = "A vehicle should typically either use this generic lumbar signal or the more specified top/mid/bottom signals.";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Seat_Backrest_LumbarSupport {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Seat_Backrest_LumbarSupport {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Seat_Backrest_MidLumbarSupport :> Real;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Backrest_MidLumbarSupport {
    path = "Vehicle.Cabin.Seat.Backrest.MidLumbarSupport";
    kind = "actuator";
    datatype = "float";
    sourceDescription = "Mid lumbar support (in/out position). 0 = Innermost position. 100 = Outermost position.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Seat_Backrest_MidLumbarSupport {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Seat_Backrest_MidLumbarSupport {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Seat_Backrest_Recline :> Real;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Backrest_Recline {
    path = "Vehicle.Cabin.Seat.Backrest.Recline";
    kind = "actuator";
    datatype = "float";
    sourceDescription = "Backrest recline compared to seat z-axis (seat vertical axis). 0 degrees = Upright/Vertical backrest. Negative degrees for forward recline. Positive degrees for backward recline.";
    sourceComment = "Seat z-axis depends on seat tilt. This means that movement of backrest due to seat tilting will not affect Backrest.Recline as long as the angle between Seating and Backrest are constant. Absolute recline relative to vehicle z-axis can be calculated as Tilt + Backrest.Recline.";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Seat_Backrest_Recline {
    quantityReference = "ISQ::planeAngle";
    unitReference = "SI::degree";
  }

  attribute def Vehicle_Cabin_Seat_Backrest_SideBolsterSupport :> Real;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Backrest_SideBolsterSupport {
    path = "Vehicle.Cabin.Seat.Backrest.SideBolsterSupport";
    kind = "actuator";
    datatype = "float";
    sourceDescription = "Side bolster support. 0 = Minimum support (widest side bolster setting). 100 = Maximum support.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Seat_Backrest_SideBolsterSupport {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Seat_Backrest_SideBolsterSupport {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Seat_Backrest_SideBolsterSupportLeft :> Real;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Backrest_SideBolsterSupportLeft {
    path = "Vehicle.Cabin.Seat.Backrest.SideBolsterSupportLeft";
    kind = "actuator";
    datatype = "float";
    sourceDescription = "Side bolster support left. 0 = Minimum support (widest side bolster setting). 100 = Maximum support.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Seat_Backrest_SideBolsterSupportLeft {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Seat_Backrest_SideBolsterSupportLeft {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Seat_Backrest_SideBolsterSupportRight :> Real;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Backrest_SideBolsterSupportRight {
    path = "Vehicle.Cabin.Seat.Backrest.SideBolsterSupportRight";
    kind = "actuator";
    datatype = "float";
    sourceDescription = "Side bolster support right. 0 = Minimum support (widest side bolster setting). 100 = Maximum support.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Seat_Backrest_SideBolsterSupportRight {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Seat_Backrest_SideBolsterSupportRight {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Seat_Backrest_TopLumbarSupport :> Real;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Backrest_TopLumbarSupport {
    path = "Vehicle.Cabin.Seat.Backrest.TopLumbarSupport";
    kind = "actuator";
    datatype = "float";
    sourceDescription = "Top lumbar support (in/out position). 0 = Innermost position. 100 = Outermost position.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Seat_Backrest_TopLumbarSupport {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Seat_Backrest_TopLumbarSupport {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Seat_Backrest_UpperShoulderSupport :> Real;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Backrest_UpperShoulderSupport {
    path = "Vehicle.Cabin.Seat.Backrest.UpperShoulderSupport";
    kind = "actuator";
    datatype = "float";
    sourceDescription = "Upper shoulder support. 0 = Minimum support (widest side bolster setting). 100 = Maximum support.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Seat_Backrest_UpperShoulderSupport {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Seat_Backrest_UpperShoulderSupport {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Seat_Headrest_Angle :> Real;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Headrest_Angle {
    path = "Vehicle.Cabin.Seat.Headrest.Angle";
    kind = "actuator";
    datatype = "float";
    sourceDescription = "Headrest angle, relative to backrest, 0 degrees if parallel to backrest, Positive degrees = tilted forward.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Seat_Headrest_Angle {
    quantityReference = "ISQ::planeAngle";
    unitReference = "SI::degree";
  }

  attribute def Vehicle_Cabin_Seat_Headrest_Height :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Headrest_Height {
    path = "Vehicle.Cabin.Seat.Headrest.Height";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Position of headrest relative to movable range of the head rest. 0 = Bottommost position supported.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Seat_Headrest_Height {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }
  @VssRangeMetadata about Vehicle_Cabin_Seat_Headrest_Height {
    minValue = "0";
    maxValue = "";
  }

  attribute def Vehicle_Cabin_Seat_Headrest_IsBackwardSwitchEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Headrest_IsBackwardSwitchEngaged {
    path = "Vehicle.Cabin.Seat.Headrest.IsBackwardSwitchEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Headrest backward switch engaged.";
    sourceComment = "Affects the property (Headrest.Angle).";
  }

  attribute def Vehicle_Cabin_Seat_Headrest_IsDownSwitchEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Headrest_IsDownSwitchEngaged {
    path = "Vehicle.Cabin.Seat.Headrest.IsDownSwitchEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Headrest down switch engaged.";
    sourceComment = "Affects the property (Headrest.Height).";
  }

  attribute def Vehicle_Cabin_Seat_Headrest_IsForwardSwitchEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Headrest_IsForwardSwitchEngaged {
    path = "Vehicle.Cabin.Seat.Headrest.IsForwardSwitchEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Headrest forward switch engaged.";
    sourceComment = "Affects the property (Headrest.Angle).";
  }

  attribute def Vehicle_Cabin_Seat_Headrest_IsUpSwitchEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Headrest_IsUpSwitchEngaged {
    path = "Vehicle.Cabin.Seat.Headrest.IsUpSwitchEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Headrest up switch engaged.";
    sourceComment = "Affects the property (Headrest.Height).";
  }

  attribute def Vehicle_Cabin_Seat_HeatingCooling :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_Seat_HeatingCooling {
    path = "Vehicle.Cabin.Seat.HeatingCooling";
    kind = "actuator";
    datatype = "int8";
    sourceDescription = "Heating or Cooling requsted for the Item. -100 = Maximum cooling, 0 = Heating/cooling deactivated, 100 = Maximum heating.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Seat_HeatingCooling {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Seat_HeatingCooling {
    minValue = "-100";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Seat_Height :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Height {
    path = "Vehicle.Cabin.Seat.Height";
    kind = "actuator";
    datatype = "uint16";
    sourceDescription = "Seat position on vehicle z-axis. Position is relative within available movable range of the seating. 0 = Lowermost position supported.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Seat_Height {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }
  @VssRangeMetadata about Vehicle_Cabin_Seat_Height {
    minValue = "0";
    maxValue = "";
  }

  attribute def Vehicle_Cabin_Seat_IsBackwardSwitchEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_IsBackwardSwitchEngaged {
    path = "Vehicle.Cabin.Seat.IsBackwardSwitchEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Seat backward switch engaged.";
    sourceComment = "Affects the property (Position).";
  }

  attribute def Vehicle_Cabin_Seat_IsBelted :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_IsBelted {
    path = "Vehicle.Cabin.Seat.IsBelted";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Is the belt engaged.";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_Seat_IsCoolerSwitchEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_IsCoolerSwitchEngaged {
    path = "Vehicle.Cabin.Seat.IsCoolerSwitchEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Cooler switch for Seat heater.";
    sourceComment = "Affects the property (HeatingCooling).";
  }

  attribute def Vehicle_Cabin_Seat_IsDecreaseMassageLevelSwitchEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_IsDecreaseMassageLevelSwitchEngaged {
    path = "Vehicle.Cabin.Seat.IsDecreaseMassageLevelSwitchEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Decrease massage level switch engaged.";
    sourceComment = "Affects the property (Massage.Level).";
  }

  attribute def Vehicle_Cabin_Seat_IsDownSwitchEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_IsDownSwitchEngaged {
    path = "Vehicle.Cabin.Seat.IsDownSwitchEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Seat down switch engaged.";
    sourceComment = "Affects the property (Height).";
  }

  attribute def Vehicle_Cabin_Seat_IsForwardSwitchEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_IsForwardSwitchEngaged {
    path = "Vehicle.Cabin.Seat.IsForwardSwitchEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Seat forward switch engaged.";
    sourceComment = "Affects the property (Position).";
  }

  attribute def Vehicle_Cabin_Seat_IsIncreaseMassageLevelSwitchEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_IsIncreaseMassageLevelSwitchEngaged {
    path = "Vehicle.Cabin.Seat.IsIncreaseMassageLevelSwitchEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Increase massage level switch engaged.";
    sourceComment = "Affects the property (Massage.Level).";
  }

  attribute def Vehicle_Cabin_Seat_IsTiltBackwardSwitchEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_IsTiltBackwardSwitchEngaged {
    path = "Vehicle.Cabin.Seat.IsTiltBackwardSwitchEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Tilt backward switch engaged.";
    sourceComment = "Affects the property (Tilt).";
  }

  attribute def Vehicle_Cabin_Seat_IsTiltForwardSwitchEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_IsTiltForwardSwitchEngaged {
    path = "Vehicle.Cabin.Seat.IsTiltForwardSwitchEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Tilt forward switch engaged.";
    sourceComment = "Affects the property (Tilt).";
  }

  attribute def Vehicle_Cabin_Seat_IsUpSwitchEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_IsUpSwitchEngaged {
    path = "Vehicle.Cabin.Seat.IsUpSwitchEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Seat up switch engaged.";
    sourceComment = "Affects the property (Height).";
  }

  attribute def Vehicle_Cabin_Seat_IsWarmerSwitchEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_IsWarmerSwitchEngaged {
    path = "Vehicle.Cabin.Seat.IsWarmerSwitchEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Warmer switch for Seat heater.";
    sourceComment = "Affects the property (HeatingCooling).";
  }

  attribute def Vehicle_Cabin_Seat_Massage_IsAvailable :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Massage_IsAvailable {
    path = "Vehicle.Cabin.Seat.Massage.IsAvailable";
    kind = "attribute";
    datatype = "boolean";
    sourceDescription = "True if the seat have the massage capability";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_Seat_Massage_Level :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Massage_Level {
    path = "Vehicle.Cabin.Seat.Massage.Level";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Seat massage level. 0 = off. 100 = max massage.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Seat_Massage_Level {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Seat_Massage_Level {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Seat_Massage_Status :> Vehicle_Cabin_Seat_Massage_Status_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Massage_Status {
    path = "Vehicle.Cabin.Seat.Massage.Status";
    kind = "sensor";
    datatype = "string";
    sourceDescription = "Massage status.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Seat_Massage_Status {
    allowedValues = "ON, OFF";
  }

  attribute def Vehicle_Cabin_Seat_Massage_SupportedTypes :> String;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Massage_SupportedTypes {
    path = "Vehicle.Cabin.Seat.Massage.SupportedTypes";
    kind = "attribute";
    datatype = "string[]";
    sourceDescription = "Type of massage.";
    sourceComment = "OEMs may define a list of identifiers for supported massage types using the allowed keyword";
  }

  attribute def Vehicle_Cabin_Seat_Massage_TypeActive :> String;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Massage_TypeActive {
    path = "Vehicle.Cabin.Seat.Massage.TypeActive";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Type of massage active.";
    sourceComment = "OEMs may define a list of identifiers for supported massage types using the allowed keyword";
  }

  attribute def Vehicle_Cabin_Seat_NeckScarf_FanSpeed :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_Seat_NeckScarf_FanSpeed {
    path = "Vehicle.Cabin.Seat.NeckScarf.FanSpeed";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Speed of the fan.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Seat_NeckScarf_FanSpeed {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Seat_NeckScarf_FanSpeed {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Seat_NeckScarf_HeatingCooling :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_Seat_NeckScarf_HeatingCooling {
    path = "Vehicle.Cabin.Seat.NeckScarf.HeatingCooling";
    kind = "actuator";
    datatype = "int8";
    sourceDescription = "Heating or Cooling requsted for the Item. -100 = Maximum cooling, 0 = Heating/cooling deactivated, 100 = Maximum heating.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Seat_NeckScarf_HeatingCooling {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Seat_NeckScarf_HeatingCooling {
    minValue = "-100";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Seat_OccupancyStatus :> Vehicle_Cabin_Seat_OccupancyStatus_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Seat_OccupancyStatus {
    path = "Vehicle.Cabin.Seat.OccupancyStatus";
    kind = "sensor";
    datatype = "string";
    sourceDescription = "Occupancy status of the seat.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Seat_OccupancyStatus {
    allowedValues = "UNKNOWN, OCCUPIED, EMPTY";
  }

  attribute def Vehicle_Cabin_Seat_Position :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Position {
    path = "Vehicle.Cabin.Seat.Position";
    kind = "actuator";
    datatype = "uint16";
    sourceDescription = "Seat position on vehicle x-axis. Position is relative to the frontmost position supported by the seat. 0 = Frontmost position supported.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Seat_Position {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }
  @VssRangeMetadata about Vehicle_Cabin_Seat_Position {
    minValue = "0";
    maxValue = "";
  }

  attribute def Vehicle_Cabin_Seat_SeatBeltHeight :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_Seat_SeatBeltHeight {
    path = "Vehicle.Cabin.Seat.SeatBeltHeight";
    kind = "actuator";
    datatype = "uint16";
    sourceDescription = "Seat belt position on vehicle z-axis. Position is relative within available movable range of the seat belt. 0 = Lowermost position supported.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Seat_SeatBeltHeight {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }

  attribute def Vehicle_Cabin_Seat_Seating_HeatingCooling :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Seating_HeatingCooling {
    path = "Vehicle.Cabin.Seat.Seating.HeatingCooling";
    kind = "actuator";
    datatype = "int8";
    sourceDescription = "Heating or Cooling requsted for the Item. -100 = Maximum cooling, 0 = Heating/cooling deactivated, 100 = Maximum heating.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Seat_Seating_HeatingCooling {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Seat_Seating_HeatingCooling {
    minValue = "-100";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Seat_Seating_IsBackwardSwitchEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Seating_IsBackwardSwitchEngaged {
    path = "Vehicle.Cabin.Seat.Seating.IsBackwardSwitchEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is switch to decrease seating length engaged.";
    sourceComment = "Affects the property (Seating.Length).";
  }

  attribute def Vehicle_Cabin_Seat_Seating_IsForwardSwitchEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Seating_IsForwardSwitchEngaged {
    path = "Vehicle.Cabin.Seat.Seating.IsForwardSwitchEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is switch to increase seating length engaged.";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_Seat_Seating_Length :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Seating_Length {
    path = "Vehicle.Cabin.Seat.Seating.Length";
    kind = "actuator";
    datatype = "uint16";
    sourceDescription = "Length adjustment of seating. 0 = Adjustable part of seating in rearmost position (Shortest length of seating).";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Seat_Seating_Length {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }
  @VssRangeMetadata about Vehicle_Cabin_Seat_Seating_Length {
    minValue = "0";
    maxValue = "";
  }

  attribute def Vehicle_Cabin_Seat_Seating_SideBolsterSupportLeft :> Real;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Seating_SideBolsterSupportLeft {
    path = "Vehicle.Cabin.Seat.Seating.SideBolsterSupportLeft";
    kind = "actuator";
    datatype = "float";
    sourceDescription = "Seat bottom side bolster support left. 0 = Minimum support (widest side bolster setting). 100 = Maximum support.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Seat_Seating_SideBolsterSupportLeft {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Seat_Seating_SideBolsterSupportLeft {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Seat_Seating_SideBolsterSupportRight :> Real;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Seating_SideBolsterSupportRight {
    path = "Vehicle.Cabin.Seat.Seating.SideBolsterSupportRight";
    kind = "actuator";
    datatype = "float";
    sourceDescription = "Seat bottom side bolster support right. 0 = Minimum support (widest side bolster setting). 100 = Maximum support.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Seat_Seating_SideBolsterSupportRight {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Seat_Seating_SideBolsterSupportRight {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Seat_Tilt :> Real;
  @VssSignalMetadata about Vehicle_Cabin_Seat_Tilt {
    path = "Vehicle.Cabin.Seat.Tilt";
    kind = "actuator";
    datatype = "float";
    sourceDescription = "Tilting of seat (seating and backrest) relative to vehicle x-axis. 0 = seat bottom is flat, seat bottom and vehicle x-axis are parallel. Positive degrees = seat tilted backwards, seat x-axis tilted upward, seat z-axis is tilted backward.";
    sourceComment = "In VSS it is assumed that tilting a seat affects both seating (seat bottom) and backrest, i.e. the angle between seating and backrest will not be affected when changing Tilt.";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Seat_Tilt {
    quantityReference = "ISQ::planeAngle";
    unitReference = "SI::degree";
  }

  attribute def Vehicle_Cabin_SeatPosCount :> ScalarValues::ScalarValue;
  @VssSignalMetadata about Vehicle_Cabin_SeatPosCount {
    path = "Vehicle.Cabin.SeatPosCount";
    kind = "attribute";
    datatype = "uint8[]";
    sourceDescription = "Number of seats across each row from the front to the rear.";
    sourceComment = "Default value corresponds to two seats in front row and 3 seats in second row.";
  }

  attribute def Vehicle_Cabin_SeatRowCount :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_SeatRowCount {
    path = "Vehicle.Cabin.SeatRowCount";
    kind = "attribute";
    datatype = "uint8";
    sourceDescription = "Number of seat rows in vehicle.";
    sourceComment = "Default value corresponds to two rows of seats.";
  }

  attribute def Vehicle_Cabin_Sunroof_Position :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_Sunroof_Position {
    path = "Vehicle.Cabin.Sunroof.Position";
    kind = "sensor";
    datatype = "int8";
    sourceDescription = "Sunroof position. 0 = Fully closed 100 = Fully opened. -100 = Fully tilted.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Sunroof_Position {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Sunroof_Position {
    minValue = "-100";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Sunroof_Shade_IsOpen :> Boolean;
  @VssSignalMetadata about Vehicle_Cabin_Sunroof_Shade_IsOpen {
    path = "Vehicle.Cabin.Sunroof.Shade.IsOpen";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is item open or closed? True = Fully or partially open. False = Fully closed.";
    sourceComment = "";
  }

  attribute def Vehicle_Cabin_Sunroof_Shade_Position :> Integer;
  @VssSignalMetadata about Vehicle_Cabin_Sunroof_Shade_Position {
    path = "Vehicle.Cabin.Sunroof.Shade.Position";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Item position. 0 = Start position 100 = End position.";
    sourceComment = "Relationship between Open/Close and Start/End position is item dependent.";
  }
  @VssQuantityMetadata about Vehicle_Cabin_Sunroof_Shade_Position {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Cabin_Sunroof_Shade_Position {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Cabin_Sunroof_Shade_Switch :> Vehicle_Cabin_Sunroof_Shade_Switch_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Sunroof_Shade_Switch {
    path = "Vehicle.Cabin.Sunroof.Shade.Switch";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Switch controlling sliding action such as window, sunroof, or blind.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Sunroof_Shade_Switch {
    allowedValues = "INACTIVE, CLOSE, OPEN, ONE_SHOT_CLOSE, ONE_SHOT_OPEN";
  }

  attribute def Vehicle_Cabin_Sunroof_Switch :> Vehicle_Cabin_Sunroof_Switch_AllowedValue;
  @VssSignalMetadata about Vehicle_Cabin_Sunroof_Switch {
    path = "Vehicle.Cabin.Sunroof.Switch";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Switch controlling sliding action such as window, sunroof, or shade.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Cabin_Sunroof_Switch {
    allowedValues = "INACTIVE, CLOSE, OPEN, ONE_SHOT_CLOSE, ONE_SHOT_OPEN, TILT_UP, TILT_DOWN";
  }

  attribute def Vehicle_CargoVolume :> Real;
  @VssSignalMetadata about Vehicle_CargoVolume {
    path = "Vehicle.CargoVolume";
    kind = "attribute";
    datatype = "float";
    sourceDescription = "The available volume for cargo or luggage. For automobiles, this is usually the trunk volume.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_CargoVolume {
    quantityReference = "ISQ::volume";
    unitReference = "SI::litre";
  }
  @VssRangeMetadata about Vehicle_CargoVolume {
    minValue = "0";
    maxValue = "";
  }

  attribute def Vehicle_Chassis_Accelerator_PedalPosition :> Integer;
  @VssSignalMetadata about Vehicle_Chassis_Accelerator_PedalPosition {
    path = "Vehicle.Chassis.Accelerator.PedalPosition";
    kind = "sensor";
    datatype = "uint8";
    sourceDescription = "Accelerator pedal position as percent. 0 = Not depressed. 100 = Fully depressed.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Chassis_Accelerator_PedalPosition {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Chassis_Accelerator_PedalPosition {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Chassis_Axle_AxleWidth :> Integer;
  @VssSignalMetadata about Vehicle_Chassis_Axle_AxleWidth {
    path = "Vehicle.Chassis.Axle.AxleWidth";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "The lateral distance between the wheel mounting faces, measured along the spindle axis.";
    sourceComment = "Corresponds to SAE J1100-2009 W113.";
  }
  @VssQuantityMetadata about Vehicle_Chassis_Axle_AxleWidth {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }

  attribute def Vehicle_Chassis_Axle_SteeringAngle :> Real;
  @VssSignalMetadata about Vehicle_Chassis_Axle_SteeringAngle {
    path = "Vehicle.Chassis.Axle.SteeringAngle";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Single track two-axle model steering angle. Angle according to ISO 8855. Positive = degrees to the left. Negative = degrees to the right.";
    sourceComment = "Single track two-axle model steering angle refers to the angle that a centrally mounted wheel would have.";
  }
  @VssQuantityMetadata about Vehicle_Chassis_Axle_SteeringAngle {
    quantityReference = "ISQ::planeAngle";
    unitReference = "SI::degree";
  }

  attribute def Vehicle_Chassis_Axle_TireAspectRatio :> Integer;
  @VssSignalMetadata about Vehicle_Chassis_Axle_TireAspectRatio {
    path = "Vehicle.Chassis.Axle.TireAspectRatio";
    kind = "attribute";
    datatype = "uint8";
    sourceDescription = "Aspect ratio between tire section height and tire section width, as per ETRTO / TRA standard.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Chassis_Axle_TireAspectRatio {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }

  attribute def Vehicle_Chassis_Axle_TireDiameter :> Real;
  @VssSignalMetadata about Vehicle_Chassis_Axle_TireDiameter {
    path = "Vehicle.Chassis.Axle.TireDiameter";
    kind = "attribute";
    datatype = "float";
    sourceDescription = "Outer diameter of tires, in inches, as per ETRTO / TRA standard.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Chassis_Axle_TireDiameter {
    quantityReference = "ISQ::length";
    unitReference = "USCustomaryUnits::inch";
  }

  attribute def Vehicle_Chassis_Axle_TireWidth :> Integer;
  @VssSignalMetadata about Vehicle_Chassis_Axle_TireWidth {
    path = "Vehicle.Chassis.Axle.TireWidth";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Nominal section width of tires, in mm, as per ETRTO / TRA standard.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Chassis_Axle_TireWidth {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }

  attribute def Vehicle_Chassis_Axle_TrackWidth :> Integer;
  @VssSignalMetadata about Vehicle_Chassis_Axle_TrackWidth {
    path = "Vehicle.Chassis.Axle.TrackWidth";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "The lateral distance between the centers of the wheels, measured along the spindle, or axle axis. If there are dual rear wheels, measure from the midway points between the inner and outer tires.";
    sourceComment = "Corresponds to SAE J1100-2009 W102.";
  }
  @VssQuantityMetadata about Vehicle_Chassis_Axle_TrackWidth {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }

  attribute def Vehicle_Chassis_Axle_TreadWidth :> Integer;
  @VssSignalMetadata about Vehicle_Chassis_Axle_TreadWidth {
    path = "Vehicle.Chassis.Axle.TreadWidth";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "The lateral distance between the centerlines of the base tires at ground, including camber angle. If there are dual rear wheels, measure from the midway points between the inner and outer tires.";
    sourceComment = "Corresponds to SAE J1100-2009 W101.";
  }
  @VssQuantityMetadata about Vehicle_Chassis_Axle_TreadWidth {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }

  attribute def Vehicle_Chassis_Axle_Wheel_AngularSpeed :> Real;
  @VssSignalMetadata about Vehicle_Chassis_Axle_Wheel_AngularSpeed {
    path = "Vehicle.Chassis.Axle.Wheel.AngularSpeed";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Angular (Rotational) speed of a vehicle's wheel.";
    sourceComment = "Positive if wheel is trying to drive vehicle forward. Negative if wheel is trying to drive vehicle backward.";
  }
  @VssQuantityMetadata about Vehicle_Chassis_Axle_Wheel_AngularSpeed {
    quantityReference = "ISQ::angularVelocity";
    unitReference = "SI::degreePerSecond";
  }

  attribute def Vehicle_Chassis_Axle_Wheel_Brake_FluidLevel :> Integer;
  @VssSignalMetadata about Vehicle_Chassis_Axle_Wheel_Brake_FluidLevel {
    path = "Vehicle.Chassis.Axle.Wheel.Brake.FluidLevel";
    kind = "sensor";
    datatype = "uint8";
    sourceDescription = "Brake fluid level as percent. 0 = Empty. 100 = Full.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Chassis_Axle_Wheel_Brake_FluidLevel {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Chassis_Axle_Wheel_Brake_FluidLevel {
    minValue = "";
    maxValue = "100";
  }

  attribute def Vehicle_Chassis_Axle_Wheel_Brake_IsBrakesWorn :> Boolean;
  @VssSignalMetadata about Vehicle_Chassis_Axle_Wheel_Brake_IsBrakesWorn {
    path = "Vehicle.Chassis.Axle.Wheel.Brake.IsBrakesWorn";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Brake pad wear status. True = Worn. False = Not Worn.";
    sourceComment = "";
  }

  attribute def Vehicle_Chassis_Axle_Wheel_Brake_IsFluidLevelLow :> Boolean;
  @VssSignalMetadata about Vehicle_Chassis_Axle_Wheel_Brake_IsFluidLevelLow {
    path = "Vehicle.Chassis.Axle.Wheel.Brake.IsFluidLevelLow";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Brake fluid level status. True = Brake fluid level low. False = Brake fluid level OK.";
    sourceComment = "";
  }

  attribute def Vehicle_Chassis_Axle_Wheel_Brake_PadWear :> Integer;
  @VssSignalMetadata about Vehicle_Chassis_Axle_Wheel_Brake_PadWear {
    path = "Vehicle.Chassis.Axle.Wheel.Brake.PadWear";
    kind = "sensor";
    datatype = "uint8";
    sourceDescription = "Brake pad wear as percent. 0 = No Wear. 100 = Worn.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Chassis_Axle_Wheel_Brake_PadWear {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Chassis_Axle_Wheel_Brake_PadWear {
    minValue = "";
    maxValue = "100";
  }

  attribute def Vehicle_Chassis_Axle_Wheel_Speed :> Real;
  @VssSignalMetadata about Vehicle_Chassis_Axle_Wheel_Speed {
    path = "Vehicle.Chassis.Axle.Wheel.Speed";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Linear speed of a vehicle's wheel.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Chassis_Axle_Wheel_Speed {
    quantityReference = "ISQ::speed";
    unitReference = "SI::kilometrePerHour";
  }

  attribute def Vehicle_Chassis_Axle_Wheel_Tire_AirTemperature :> Real;
  @VssSignalMetadata about Vehicle_Chassis_Axle_Wheel_Tire_AirTemperature {
    path = "Vehicle.Chassis.Axle.Wheel.Tire.AirTemperature";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Air temperature inside the tire in Celsius.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Chassis_Axle_Wheel_Tire_AirTemperature {
    quantityReference = "ISQ::thermodynamicTemperature";
    unitReference = "SI::degreeCelsius";
  }

  attribute def Vehicle_Chassis_Axle_Wheel_Tire_IsPressureLow :> Boolean;
  @VssSignalMetadata about Vehicle_Chassis_Axle_Wheel_Tire_IsPressureLow {
    path = "Vehicle.Chassis.Axle.Wheel.Tire.IsPressureLow";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Tire Pressure Status. True = Low tire pressure. False = Good tire pressure.";
    sourceComment = "";
  }

  attribute def Vehicle_Chassis_Axle_Wheel_Tire_Pressure :> Integer;
  @VssSignalMetadata about Vehicle_Chassis_Axle_Wheel_Tire_Pressure {
    path = "Vehicle.Chassis.Axle.Wheel.Tire.Pressure";
    kind = "sensor";
    datatype = "uint16";
    sourceDescription = "Tire pressure in kilo-Pascal.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Chassis_Axle_Wheel_Tire_Pressure {
    quantityReference = "ISQ::pressure";
    unitReference = "SI::kilopascal";
  }

  attribute def Vehicle_Chassis_Axle_Wheel_Tire_RubberTemperature :> Real;
  @VssSignalMetadata about Vehicle_Chassis_Axle_Wheel_Tire_RubberTemperature {
    path = "Vehicle.Chassis.Axle.Wheel.Tire.RubberTemperature";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Rubber temperature of the tire in Celsius.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Chassis_Axle_Wheel_Tire_RubberTemperature {
    quantityReference = "ISQ::thermodynamicTemperature";
    unitReference = "SI::degreeCelsius";
  }

  attribute def Vehicle_Chassis_Axle_Wheel_Tire_Temperature :> Real;
  @VssSignalMetadata about Vehicle_Chassis_Axle_Wheel_Tire_Temperature {
    path = "Vehicle.Chassis.Axle.Wheel.Tire.Temperature";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Tire temperature in Celsius.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Chassis_Axle_Wheel_Tire_Temperature {
    quantityReference = "ISQ::thermodynamicTemperature";
    unitReference = "SI::degreeCelsius";
  }

  attribute def Vehicle_Chassis_Axle_WheelCount :> Integer;
  @VssSignalMetadata about Vehicle_Chassis_Axle_WheelCount {
    path = "Vehicle.Chassis.Axle.WheelCount";
    kind = "attribute";
    datatype = "uint8";
    sourceDescription = "Number of wheels on the axle";
    sourceComment = "";
  }

  attribute def Vehicle_Chassis_Axle_WheelDiameter :> Real;
  @VssSignalMetadata about Vehicle_Chassis_Axle_WheelDiameter {
    path = "Vehicle.Chassis.Axle.WheelDiameter";
    kind = "attribute";
    datatype = "float";
    sourceDescription = "Diameter of wheels (rims without tires), in inches, as per ETRTO / TRA standard.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Chassis_Axle_WheelDiameter {
    quantityReference = "ISQ::length";
    unitReference = "USCustomaryUnits::inch";
  }

  attribute def Vehicle_Chassis_Axle_WheelWidth :> Real;
  @VssSignalMetadata about Vehicle_Chassis_Axle_WheelWidth {
    path = "Vehicle.Chassis.Axle.WheelWidth";
    kind = "attribute";
    datatype = "float";
    sourceDescription = "Width of wheels (rims without tires), in inches, as per ETRTO / TRA standard.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Chassis_Axle_WheelWidth {
    quantityReference = "ISQ::length";
    unitReference = "USCustomaryUnits::inch";
  }

  attribute def Vehicle_Chassis_AxleCount :> Integer;
  @VssSignalMetadata about Vehicle_Chassis_AxleCount {
    path = "Vehicle.Chassis.AxleCount";
    kind = "attribute";
    datatype = "uint8";
    sourceDescription = "Number of axles on the vehicle";
    sourceComment = "";
  }

  attribute def Vehicle_Chassis_Brake_IsDriverEmergencyBrakingDetected :> Boolean;
  @VssSignalMetadata about Vehicle_Chassis_Brake_IsDriverEmergencyBrakingDetected {
    path = "Vehicle.Chassis.Brake.IsDriverEmergencyBrakingDetected";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if emergency braking initiated by driver is detected. True = Emergency braking detected. False = Emergency braking not detected.";
    sourceComment = "Detection of emergency braking can trigger Emergency Brake Assist (EBA) to engage.";
  }

  attribute def Vehicle_Chassis_Brake_PedalPosition :> Integer;
  @VssSignalMetadata about Vehicle_Chassis_Brake_PedalPosition {
    path = "Vehicle.Chassis.Brake.PedalPosition";
    kind = "sensor";
    datatype = "uint8";
    sourceDescription = "Brake pedal position as percent. 0 = Not depressed. 100 = Fully depressed.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Chassis_Brake_PedalPosition {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Chassis_Brake_PedalPosition {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Chassis_ParkingBrake_IsAutoApplyEnabled :> Boolean;
  @VssSignalMetadata about Vehicle_Chassis_ParkingBrake_IsAutoApplyEnabled {
    path = "Vehicle.Chassis.ParkingBrake.IsAutoApplyEnabled";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Indicates if parking brake will be automatically engaged when the vehicle engine is turned off.";
    sourceComment = "";
  }

  attribute def Vehicle_Chassis_ParkingBrake_IsEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Chassis_ParkingBrake_IsEngaged {
    path = "Vehicle.Chassis.ParkingBrake.IsEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Parking brake status. True = Parking Brake is Engaged. False = Parking Brake is not Engaged.";
    sourceComment = "";
  }

  attribute def Vehicle_Chassis_SteeringWheel_Angle :> Integer;
  @VssSignalMetadata about Vehicle_Chassis_SteeringWheel_Angle {
    path = "Vehicle.Chassis.SteeringWheel.Angle";
    kind = "sensor";
    datatype = "int16";
    sourceDescription = "Steering wheel angle. Positive = degrees to the left. Negative = degrees to the right.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Chassis_SteeringWheel_Angle {
    quantityReference = "ISQ::planeAngle";
    unitReference = "SI::degree";
  }

  attribute def Vehicle_Chassis_SteeringWheel_Extension :> Integer;
  @VssSignalMetadata about Vehicle_Chassis_SteeringWheel_Extension {
    path = "Vehicle.Chassis.SteeringWheel.Extension";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Steering wheel column extension from dashboard. 0 = Closest to dashboard. 100 = Furthest from dashboard.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Chassis_SteeringWheel_Extension {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Chassis_SteeringWheel_Extension {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Chassis_SteeringWheel_HeatingCooling :> Integer;
  @VssSignalMetadata about Vehicle_Chassis_SteeringWheel_HeatingCooling {
    path = "Vehicle.Chassis.SteeringWheel.HeatingCooling";
    kind = "actuator";
    datatype = "int8";
    sourceDescription = "Heating or Cooling requsted for the Item. -100 = Maximum cooling, 0 = Heating/cooling deactivated, 100 = Maximum heating.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Chassis_SteeringWheel_HeatingCooling {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Chassis_SteeringWheel_HeatingCooling {
    minValue = "-100";
    maxValue = "100";
  }

  attribute def Vehicle_Chassis_SteeringWheel_Tilt :> Integer;
  @VssSignalMetadata about Vehicle_Chassis_SteeringWheel_Tilt {
    path = "Vehicle.Chassis.SteeringWheel.Tilt";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Steering wheel column tilt. 0 = Lowest position. 100 = Highest position.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Chassis_SteeringWheel_Tilt {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Chassis_SteeringWheel_Tilt {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Chassis_Wheelbase :> Integer;
  @VssSignalMetadata about Vehicle_Chassis_Wheelbase {
    path = "Vehicle.Chassis.Wheelbase";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Overall wheelbase, in mm.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Chassis_Wheelbase {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }

  attribute def Vehicle_Connectivity_IsConnectivityAvailable :> Boolean;
  @VssSignalMetadata about Vehicle_Connectivity_IsConnectivityAvailable {
    path = "Vehicle.Connectivity.IsConnectivityAvailable";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if connectivity between vehicle and cloud is available. True = Connectivity is available. False = Connectivity is not available.";
    sourceComment = "This signal can be used by onboard vehicle services to decide what features that shall be offered to the driver, for example disable the 'check for update' button if vehicle does not have connectivity.";
  }

  attribute def Vehicle_ControlUnit_Health_Network_CAN_IsNetworkOK :> Boolean;
  @VssSignalMetadata about Vehicle_ControlUnit_Health_Network_CAN_IsNetworkOK {
    path = "Vehicle.ControlUnit.Health.Network.CAN.IsNetworkOK";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Network status. True = No network problems detected. False = Network problems detected.";
    sourceComment = "";
  }

  attribute def Vehicle_ControlUnit_Health_Network_ETH_IsNetworkOK :> Boolean;
  @VssSignalMetadata about Vehicle_ControlUnit_Health_Network_ETH_IsNetworkOK {
    path = "Vehicle.ControlUnit.Health.Network.ETH.IsNetworkOK";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Network status. True = No network problems detected. False = Network problems detected.";
    sourceComment = "";
  }

  attribute def Vehicle_ControlUnit_Health_Resources_Power :> Real;
  @VssSignalMetadata about Vehicle_ControlUnit_Health_Resources_Power {
    path = "Vehicle.ControlUnit.Health.Resources.Power";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Power consumption";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_ControlUnit_Health_Resources_Power {
    quantityReference = "ISQ::power";
    unitReference = "SI::watt";
  }

  attribute def Vehicle_ControlUnit_Health_Resources_Temperature :> Real;
  @VssSignalMetadata about Vehicle_ControlUnit_Health_Resources_Temperature {
    path = "Vehicle.ControlUnit.Health.Resources.Temperature";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Instance temperature";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_ControlUnit_Health_Resources_Temperature {
    quantityReference = "ISQ::thermodynamicTemperature";
    unitReference = "SI::degreeCelsius";
  }

  attribute def Vehicle_ControlUnit_Health_Resources_Utilization_CPU :> Real;
  @VssSignalMetadata about Vehicle_ControlUnit_Health_Resources_Utilization_CPU {
    path = "Vehicle.ControlUnit.Health.Resources.Utilization.CPU";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "CPU utilization";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_ControlUnit_Health_Resources_Utilization_CPU {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_ControlUnit_Health_Resources_Utilization_CPU {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_ControlUnit_Health_Resources_Utilization_Memory :> Real;
  @VssSignalMetadata about Vehicle_ControlUnit_Health_Resources_Utilization_Memory {
    path = "Vehicle.ControlUnit.Health.Resources.Utilization.Memory";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Memory utilization";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_ControlUnit_Health_Resources_Utilization_Memory {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_ControlUnit_Health_Resources_Utilization_Memory {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_ControlUnit_Health_SWSupervision_IsAliveTriggered :> Boolean;
  @VssSignalMetadata about Vehicle_ControlUnit_Health_SWSupervision_IsAliveTriggered {
    path = "Vehicle.ControlUnit.Health.SWSupervision.IsAliveTriggered";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Whether the alive supervision was triggered";
    sourceComment = "";
  }

  attribute def Vehicle_ControlUnit_Health_SWSupervision_IsDeadlineTriggered :> Boolean;
  @VssSignalMetadata about Vehicle_ControlUnit_Health_SWSupervision_IsDeadlineTriggered {
    path = "Vehicle.ControlUnit.Health.SWSupervision.IsDeadlineTriggered";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Whether the deadline supervision was triggered";
    sourceComment = "";
  }

  attribute def Vehicle_ControlUnit_Health_SWSupervision_IsLogicalTriggered :> Boolean;
  @VssSignalMetadata about Vehicle_ControlUnit_Health_SWSupervision_IsLogicalTriggered {
    path = "Vehicle.ControlUnit.Health.SWSupervision.IsLogicalTriggered";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Whether the logical supervision was triggered";
    sourceComment = "";
  }

  attribute def Vehicle_ControlUnit_Health_SWSupervision_IsWatchdogTriggered :> Boolean;
  @VssSignalMetadata about Vehicle_ControlUnit_Health_SWSupervision_IsWatchdogTriggered {
    path = "Vehicle.ControlUnit.Health.SWSupervision.IsWatchdogTriggered";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Whether the watchdog deadline was triggered";
    sourceComment = "";
  }

  attribute def Vehicle_ControlUnit_ID :> Integer;
  @VssSignalMetadata about Vehicle_ControlUnit_ID {
    path = "Vehicle.ControlUnit.ID";
    kind = "attribute";
    datatype = "uint8";
    sourceDescription = "Control unit ID";
    sourceComment = "";
  }

  attribute def Vehicle_CurbWeight :> Integer;
  @VssSignalMetadata about Vehicle_CurbWeight {
    path = "Vehicle.CurbWeight";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Vehicle curb weight, including all liquids and full tank of fuel, but no cargo or passengers.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_CurbWeight {
    quantityReference = "ISQ::mass";
    unitReference = "SI::kilogram";
  }

  attribute def Vehicle_CurrentLocation_Altitude :> Real;
  @VssSignalMetadata about Vehicle_CurrentLocation_Altitude {
    path = "Vehicle.CurrentLocation.Altitude";
    kind = "sensor";
    datatype = "double";
    sourceDescription = "Current altitude relative to WGS 84 reference ellipsoid, as measured at the position of GNSS receiver antenna.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_CurrentLocation_Altitude {
    quantityReference = "ISQ::length";
    unitReference = "SI::metre";
  }

  attribute def Vehicle_CurrentLocation_GNSSReceiver_FixType :> Vehicle_CurrentLocation_GNSSReceiver_FixType_AllowedValue;
  @VssSignalMetadata about Vehicle_CurrentLocation_GNSSReceiver_FixType {
    path = "Vehicle.CurrentLocation.GNSSReceiver.FixType";
    kind = "sensor";
    datatype = "string";
    sourceDescription = "Fix status of GNSS receiver.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_CurrentLocation_GNSSReceiver_FixType {
    allowedValues = "NONE, TWO_D, TWO_D_SATELLITE_BASED_AUGMENTATION, TWO_D_GROUND_BASED_AUGMENTATION, TWO_D_SATELLITE_AND_GROUND_BASED_AUGMENTATION, THREE_D, THREE_D_SATELLITE_BASED_AUGMENTATION, THREE_D_GROUND_BASED_AUGMENTATION, THREE_D_SATELLITE_AND_GROUND_BASED_AUGMENTATION";
  }

  attribute def Vehicle_CurrentLocation_GNSSReceiver_MountingPosition_X :> Integer;
  @VssSignalMetadata about Vehicle_CurrentLocation_GNSSReceiver_MountingPosition_X {
    path = "Vehicle.CurrentLocation.GNSSReceiver.MountingPosition.X";
    kind = "attribute";
    datatype = "int16";
    sourceDescription = "Mounting position of GNSS receiver antenna relative to vehicle coordinate system. Axis definitions according to ISO 8855. Origin at center of (first) rear axle. Positive values = forward of rear axle. Negative values = backward of rear axle.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_CurrentLocation_GNSSReceiver_MountingPosition_X {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }

  attribute def Vehicle_CurrentLocation_GNSSReceiver_MountingPosition_Y :> Integer;
  @VssSignalMetadata about Vehicle_CurrentLocation_GNSSReceiver_MountingPosition_Y {
    path = "Vehicle.CurrentLocation.GNSSReceiver.MountingPosition.Y";
    kind = "attribute";
    datatype = "int16";
    sourceDescription = "Mounting position of GNSS receiver antenna relative to vehicle coordinate system. Axis definitions according to ISO 8855. Origin at center of (first) rear axle. Positive values = left of origin. Negative values = right of origin. Left/Right is as seen from driver perspective, i.e. by a person looking forward.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_CurrentLocation_GNSSReceiver_MountingPosition_Y {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }

  attribute def Vehicle_CurrentLocation_GNSSReceiver_MountingPosition_Z :> Integer;
  @VssSignalMetadata about Vehicle_CurrentLocation_GNSSReceiver_MountingPosition_Z {
    path = "Vehicle.CurrentLocation.GNSSReceiver.MountingPosition.Z";
    kind = "attribute";
    datatype = "int16";
    sourceDescription = "Mounting position of GNSS receiver on Z-axis. Axis definitions according to ISO 8855. Origin at center of (first) rear axle. Positive values = above center of rear axle. Negative values = below center of rear axle.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_CurrentLocation_GNSSReceiver_MountingPosition_Z {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }

  attribute def Vehicle_CurrentLocation_Heading :> Real;
  @VssSignalMetadata about Vehicle_CurrentLocation_Heading {
    path = "Vehicle.CurrentLocation.Heading";
    kind = "sensor";
    datatype = "double";
    sourceDescription = "Current heading relative to geographic north. 0 = North, 90 = East, 180 = South, 270 = West.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_CurrentLocation_Heading {
    quantityReference = "ISQ::planeAngle";
    unitReference = "SI::degree";
  }
  @VssRangeMetadata about Vehicle_CurrentLocation_Heading {
    minValue = "0";
    maxValue = "360";
  }

  attribute def Vehicle_CurrentLocation_HorizontalAccuracy :> Real;
  @VssSignalMetadata about Vehicle_CurrentLocation_HorizontalAccuracy {
    path = "Vehicle.CurrentLocation.HorizontalAccuracy";
    kind = "sensor";
    datatype = "double";
    sourceDescription = "Accuracy of the latitude and longitude coordinates.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_CurrentLocation_HorizontalAccuracy {
    quantityReference = "ISQ::length";
    unitReference = "SI::metre";
  }

  attribute def Vehicle_CurrentLocation_Latitude :> Real;
  @VssSignalMetadata about Vehicle_CurrentLocation_Latitude {
    path = "Vehicle.CurrentLocation.Latitude";
    kind = "sensor";
    datatype = "double";
    sourceDescription = "Current latitude of vehicle in WGS 84 geodetic coordinates, as measured at the position of GNSS receiver antenna.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_CurrentLocation_Latitude {
    quantityReference = "ISQ::planeAngle";
    unitReference = "SI::degree";
  }
  @VssRangeMetadata about Vehicle_CurrentLocation_Latitude {
    minValue = "-90";
    maxValue = "90";
  }

  attribute def Vehicle_CurrentLocation_Longitude :> Real;
  @VssSignalMetadata about Vehicle_CurrentLocation_Longitude {
    path = "Vehicle.CurrentLocation.Longitude";
    kind = "sensor";
    datatype = "double";
    sourceDescription = "Current longitude of vehicle in WGS 84 geodetic coordinates, as measured at the position of GNSS receiver antenna.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_CurrentLocation_Longitude {
    quantityReference = "ISQ::planeAngle";
    unitReference = "SI::degree";
  }
  @VssRangeMetadata about Vehicle_CurrentLocation_Longitude {
    minValue = "-180";
    maxValue = "180";
  }

  attribute def Vehicle_CurrentLocation_Timestamp :> String;
  @VssSignalMetadata about Vehicle_CurrentLocation_Timestamp {
    path = "Vehicle.CurrentLocation.Timestamp";
    kind = "sensor";
    datatype = "string";
    sourceDescription = "Timestamp from GNSS system for current location, formatted according to ISO 8601 with UTC time zone.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_CurrentLocation_Timestamp {
    quantityReference = "n/a";
    unitReference = "ISO 8601 lexical date/time string";
  }

  attribute def Vehicle_CurrentLocation_VerticalAccuracy :> Real;
  @VssSignalMetadata about Vehicle_CurrentLocation_VerticalAccuracy {
    path = "Vehicle.CurrentLocation.VerticalAccuracy";
    kind = "sensor";
    datatype = "double";
    sourceDescription = "Accuracy of altitude.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_CurrentLocation_VerticalAccuracy {
    quantityReference = "ISQ::length";
    unitReference = "SI::metre";
  }

  attribute def Vehicle_CurrentOverallWeight :> Integer;
  @VssSignalMetadata about Vehicle_CurrentOverallWeight {
    path = "Vehicle.CurrentOverallWeight";
    kind = "sensor";
    datatype = "uint16";
    sourceDescription = "Current overall Vehicle weight. Including passengers, cargo and other load inside the car.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_CurrentOverallWeight {
    quantityReference = "ISQ::mass";
    unitReference = "SI::kilogram";
  }

  attribute def Vehicle_Diagnostics_DTCCount :> Integer;
  @VssSignalMetadata about Vehicle_Diagnostics_DTCCount {
    path = "Vehicle.Diagnostics.DTCCount";
    kind = "sensor";
    datatype = "uint8";
    sourceDescription = "Number of Diagnostic Trouble Codes (DTC)";
    sourceComment = "";
  }

  attribute def Vehicle_Diagnostics_DTCList :> String;
  @VssSignalMetadata about Vehicle_Diagnostics_DTCList {
    path = "Vehicle.Diagnostics.DTCList";
    kind = "sensor";
    datatype = "string[]";
    sourceDescription = "List of currently active DTCs formatted according OBD II (SAE-J2012DA_201812) standard ([P|C|B|U]XXXXX )";
    sourceComment = "";
  }

  attribute def Vehicle_Driver_AttentiveProbability :> Real;
  @VssSignalMetadata about Vehicle_Driver_AttentiveProbability {
    path = "Vehicle.Driver.AttentiveProbability";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Probability of attentiveness of the driver.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Driver_AttentiveProbability {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Driver_AttentiveProbability {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Driver_DistractionLevel :> Real;
  @VssSignalMetadata about Vehicle_Driver_DistractionLevel {
    path = "Vehicle.Driver.DistractionLevel";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Distraction level of the driver, which can be evaluated by multiple factors e.g. driving situation, acoustical or optical signals inside the cockpit, ongoing phone calls.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Driver_DistractionLevel {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Driver_DistractionLevel {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Driver_FatigueLevel :> Real;
  @VssSignalMetadata about Vehicle_Driver_FatigueLevel {
    path = "Vehicle.Driver.FatigueLevel";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Fatigue level of the driver, which can be evaluated by multiple factors e.g. trip time, behaviour of steering, eye status.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Driver_FatigueLevel {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Driver_FatigueLevel {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Driver_HeartRate :> Integer;
  @VssSignalMetadata about Vehicle_Driver_HeartRate {
    path = "Vehicle.Driver.HeartRate";
    kind = "sensor";
    datatype = "uint16";
    sourceDescription = "Heart rate of the driver.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Driver_HeartRate {
    quantityReference = "ISQ::frequency";
    unitReference = "SI-derived beats/minute";
  }

  attribute def Vehicle_Driver_IsEyesOnRoad :> Boolean;
  @VssSignalMetadata about Vehicle_Driver_IsEyesOnRoad {
    path = "Vehicle.Driver.IsEyesOnRoad";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Has driver the eyes on road or not?";
    sourceComment = "";
  }

  attribute def Vehicle_Driver_IsHandsOnWheel :> Boolean;
  @VssSignalMetadata about Vehicle_Driver_IsHandsOnWheel {
    path = "Vehicle.Driver.IsHandsOnWheel";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Are the driver's hands on the steering wheel or not?";
    sourceComment = "";
  }

  attribute def Vehicle_EmissionsCO2 :> Integer;
  @VssSignalMetadata about Vehicle_EmissionsCO2 {
    path = "Vehicle.EmissionsCO2";
    kind = "attribute";
    datatype = "int16";
    sourceDescription = "The CO2 emissions.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_EmissionsCO2 {
    quantityReference = "ISQ::linearDensity";
    unitReference = "SI-derived gram/kilometre";
  }

  attribute def Vehicle_Exterior_AirTemperature :> Real;
  @VssSignalMetadata about Vehicle_Exterior_AirTemperature {
    path = "Vehicle.Exterior.AirTemperature";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Air temperature outside the vehicle.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Exterior_AirTemperature {
    quantityReference = "ISQ::thermodynamicTemperature";
    unitReference = "SI::degreeCelsius";
  }

  attribute def Vehicle_Exterior_Humidity :> Real;
  @VssSignalMetadata about Vehicle_Exterior_Humidity {
    path = "Vehicle.Exterior.Humidity";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Relative humidity outside the vehicle. 0 = Dry, 100 = Air fully saturated.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Exterior_Humidity {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Exterior_Humidity {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Exterior_LightIntensity :> Real;
  @VssSignalMetadata about Vehicle_Exterior_LightIntensity {
    path = "Vehicle.Exterior.LightIntensity";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Light intensity outside the vehicle. 0 = No light detected, 100 = Fully lit.";
    sourceComment = "Mapping to physical units and calculation method is sensor specific.";
  }
  @VssQuantityMetadata about Vehicle_Exterior_LightIntensity {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Exterior_LightIntensity {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_GrossWeight :> Integer;
  @VssSignalMetadata about Vehicle_GrossWeight {
    path = "Vehicle.GrossWeight";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Curb weight of vehicle, including all liquids and full tank of fuel and full load of cargo and passengers.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_GrossWeight {
    quantityReference = "ISQ::mass";
    unitReference = "SI::kilogram";
  }

  attribute def Vehicle_Height :> Integer;
  @VssSignalMetadata about Vehicle_Height {
    path = "Vehicle.Height";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Overall vehicle height.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Height {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }

  attribute def Vehicle_IsAutoPowerOptimize :> Boolean;
  @VssSignalMetadata about Vehicle_IsAutoPowerOptimize {
    path = "Vehicle.IsAutoPowerOptimize";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Auto Power Optimization Flag When set to 'true', the system enables automatic power optimization, dynamically adjusting the power optimization level based on runtime conditions or features managed by the OEM. When set to 'false', manual control of the power optimization level is allowed.";
    sourceComment = "";
  }

  attribute def Vehicle_IsBrokenDown :> Boolean;
  @VssSignalMetadata about Vehicle_IsBrokenDown {
    path = "Vehicle.IsBrokenDown";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Vehicle breakdown or any similar event causing vehicle to stop on the road, that might pose a risk to other road users. True = Vehicle broken down on the road, due to e.g. engine problems, flat tire, out of gas, brake problems. False = Vehicle not broken down.";
    sourceComment = "Actual criteria and method used to decide if a vehicle is broken down is implementation specific.";
  }

  attribute def Vehicle_IsMoving :> Boolean;
  @VssSignalMetadata about Vehicle_IsMoving {
    path = "Vehicle.IsMoving";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates whether the vehicle is stationary or moving.";
    sourceComment = "";
  }

  attribute def Vehicle_Length :> Integer;
  @VssSignalMetadata about Vehicle_Length {
    path = "Vehicle.Length";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Overall vehicle length.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Length {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }

  attribute def Vehicle_LowVoltageBattery_CurrentCurrent :> Real;
  @VssSignalMetadata about Vehicle_LowVoltageBattery_CurrentCurrent {
    path = "Vehicle.LowVoltageBattery.CurrentCurrent";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Current current flowing in/out of the low voltage battery. Positive = Current flowing in to battery, e.g. during charging or driving. Negative = Current flowing out of battery, e.g. when using the battery to start a combustion engine.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_LowVoltageBattery_CurrentCurrent {
    quantityReference = "ISQ::electricCurrent";
    unitReference = "SI::ampere";
  }

  attribute def Vehicle_LowVoltageBattery_CurrentVoltage :> Real;
  @VssSignalMetadata about Vehicle_LowVoltageBattery_CurrentVoltage {
    path = "Vehicle.LowVoltageBattery.CurrentVoltage";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Current Voltage of the low voltage battery.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_LowVoltageBattery_CurrentVoltage {
    quantityReference = "ISQ::electricPotential";
    unitReference = "SI::volt";
  }

  attribute def Vehicle_LowVoltageBattery_NominalCapacity :> Integer;
  @VssSignalMetadata about Vehicle_LowVoltageBattery_NominalCapacity {
    path = "Vehicle.LowVoltageBattery.NominalCapacity";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Nominal capacity of the low voltage battery.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_LowVoltageBattery_NominalCapacity {
    quantityReference = "ISQ::electricCharge";
    unitReference = "SI::ampereHour";
  }

  attribute def Vehicle_LowVoltageBattery_NominalVoltage :> Integer;
  @VssSignalMetadata about Vehicle_LowVoltageBattery_NominalVoltage {
    path = "Vehicle.LowVoltageBattery.NominalVoltage";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Nominal Voltage of the battery.";
    sourceComment = "Nominal voltage typically refers to voltage of fully charged battery when delivering rated capacity.";
  }
  @VssQuantityMetadata about Vehicle_LowVoltageBattery_NominalVoltage {
    quantityReference = "ISQ::electricPotential";
    unitReference = "SI::volt";
  }

  attribute def Vehicle_LowVoltageSystemState :> Vehicle_LowVoltageSystemState_AllowedValue;
  @VssSignalMetadata about Vehicle_LowVoltageSystemState {
    path = "Vehicle.LowVoltageSystemState";
    kind = "sensor";
    datatype = "string";
    sourceDescription = "State of the supply voltage of the control units (usually 12V).";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_LowVoltageSystemState {
    allowedValues = "UNDEFINED, LOCK, OFF, ACC, ON, START";
  }

  attribute def Vehicle_MaxTowBallWeight :> Integer;
  @VssSignalMetadata about Vehicle_MaxTowBallWeight {
    path = "Vehicle.MaxTowBallWeight";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Maximum vertical weight on the tow ball of a trailer.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MaxTowBallWeight {
    quantityReference = "ISQ::mass";
    unitReference = "SI::kilogram";
  }

  attribute def Vehicle_MaxTowWeight :> Integer;
  @VssSignalMetadata about Vehicle_MaxTowWeight {
    path = "Vehicle.MaxTowWeight";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Maximum weight of trailer.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MaxTowWeight {
    quantityReference = "ISQ::mass";
    unitReference = "SI::kilogram";
  }

  attribute def Vehicle_MotionManagement_Brake_Axle_TorqueDistributionFrictionRightMaximum :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Brake_Axle_TorqueDistributionFrictionRightMaximum {
    path = "Vehicle.MotionManagement.Brake.Axle.TorqueDistributionFrictionRightMaximum";
    kind = "actuator";
    datatype = "uint16";
    sourceDescription = "Maximum distribution range of the friction brake request on the axle to the right wheel. 0% = Complete friction torque shall be shifted to the left wheel. 50% = At most 50% friction torque may be shifted to the right wheel. 100% = Complete friction torque may be shifted to the right wheel.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Brake_Axle_TorqueDistributionFrictionRightMaximum {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_MotionManagement_Brake_Axle_TorqueDistributionFrictionRightMaximum {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_MotionManagement_Brake_Axle_TorqueDistributionFrictionRightMinimum :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Brake_Axle_TorqueDistributionFrictionRightMinimum {
    path = "Vehicle.MotionManagement.Brake.Axle.TorqueDistributionFrictionRightMinimum";
    kind = "actuator";
    datatype = "uint16";
    sourceDescription = "Minimum distribution range of the friction brake request on the axle to the right wheel. 0% = Complete friction torque may be shifted to the left wheel. 50% = At least 50% friction torque shall be shifted to the right wheel. 100% = Complete friction torque shall be shifted to the right wheel.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Brake_Axle_TorqueDistributionFrictionRightMinimum {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_MotionManagement_Brake_Axle_TorqueDistributionFrictionRightMinimum {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_MotionManagement_Brake_Axle_TorqueElectricMinimum :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Brake_Axle_TorqueElectricMinimum {
    path = "Vehicle.MotionManagement.Brake.Axle.TorqueElectricMinimum";
    kind = "actuator";
    datatype = "int16";
    sourceDescription = "Limit for regenerative brake torque at given axle. Brake Torque < 0Nm.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Brake_Axle_TorqueElectricMinimum {
    quantityReference = "ISQ::momentOfForce";
    unitReference = "SI::newtonMetre";
  }
  @VssRangeMetadata about Vehicle_MotionManagement_Brake_Axle_TorqueElectricMinimum {
    minValue = "";
    maxValue = "0";
  }

  attribute def Vehicle_MotionManagement_Brake_Axle_TorqueFrictionDifferenceMaximum :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Brake_Axle_TorqueFrictionDifferenceMaximum {
    path = "Vehicle.MotionManagement.Brake.Axle.TorqueFrictionDifferenceMaximum";
    kind = "actuator";
    datatype = "uint16";
    sourceDescription = "Maximum absolute wheel torque difference between left and right wheel for friction brake.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Brake_Axle_TorqueFrictionDifferenceMaximum {
    quantityReference = "ISQ::momentOfForce";
    unitReference = "SI::newtonMetre";
  }

  attribute def Vehicle_MotionManagement_Brake_Axle_Wheel_OmegaLower :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Brake_Axle_Wheel_OmegaLower {
    path = "Vehicle.MotionManagement.Brake.Axle.Wheel.OmegaLower";
    kind = "actuator";
    datatype = "uint16";
    sourceDescription = "Lower wheel speed limit request controlled by friction brake. ISO 8855 wheel-spin velocity.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Brake_Axle_Wheel_OmegaLower {
    quantityReference = "ISQ::angularVelocity";
    unitReference = "SI::radianPerSecond";
  }

  attribute def Vehicle_MotionManagement_Brake_Axle_Wheel_OmegaUpper :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Brake_Axle_Wheel_OmegaUpper {
    path = "Vehicle.MotionManagement.Brake.Axle.Wheel.OmegaUpper";
    kind = "actuator";
    datatype = "uint16";
    sourceDescription = "Upper wheel speed limit request controlled by friction brake. ISO 8855 wheel-spin velocity.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Brake_Axle_Wheel_OmegaUpper {
    quantityReference = "ISQ::angularVelocity";
    unitReference = "SI::radianPerSecond";
  }

  attribute def Vehicle_MotionManagement_Brake_Axle_Wheel_Torque :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Brake_Axle_Wheel_Torque {
    path = "Vehicle.MotionManagement.Brake.Axle.Wheel.Torque";
    kind = "sensor";
    datatype = "int16";
    sourceDescription = "Estimated friction brake torque. Brake Torque < 0Nm.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Brake_Axle_Wheel_Torque {
    quantityReference = "ISQ::momentOfForce";
    unitReference = "SI::newtonMetre";
  }
  @VssRangeMetadata about Vehicle_MotionManagement_Brake_Axle_Wheel_Torque {
    minValue = "";
    maxValue = "0";
  }

  attribute def Vehicle_MotionManagement_Brake_Axle_Wheel_TorqueArbitrated :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Brake_Axle_Wheel_TorqueArbitrated {
    path = "Vehicle.MotionManagement.Brake.Axle.Wheel.TorqueArbitrated";
    kind = "sensor";
    datatype = "int16";
    sourceDescription = "Brake system internally calculated friction brake torque target. Brake Torque < 0Nm.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Brake_Axle_Wheel_TorqueArbitrated {
    quantityReference = "ISQ::momentOfForce";
    unitReference = "SI::newtonMetre";
  }
  @VssRangeMetadata about Vehicle_MotionManagement_Brake_Axle_Wheel_TorqueArbitrated {
    minValue = "";
    maxValue = "0";
  }

  attribute def Vehicle_MotionManagement_Brake_Axle_Wheel_TorqueFrictionMaximum :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Brake_Axle_Wheel_TorqueFrictionMaximum {
    path = "Vehicle.MotionManagement.Brake.Axle.Wheel.TorqueFrictionMaximum";
    kind = "actuator";
    datatype = "int16";
    sourceDescription = "Maximum wheel torque request for friction brake. Brake Torque < 0Nm.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Brake_Axle_Wheel_TorqueFrictionMaximum {
    quantityReference = "ISQ::momentOfForce";
    unitReference = "SI::newtonMetre";
  }
  @VssRangeMetadata about Vehicle_MotionManagement_Brake_Axle_Wheel_TorqueFrictionMaximum {
    minValue = "";
    maxValue = "0";
  }

  attribute def Vehicle_MotionManagement_Brake_Axle_Wheel_TorqueFrictionMinimum :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Brake_Axle_Wheel_TorqueFrictionMinimum {
    path = "Vehicle.MotionManagement.Brake.Axle.Wheel.TorqueFrictionMinimum";
    kind = "actuator";
    datatype = "int16";
    sourceDescription = "Minimum wheel torque request for friction brake. Brake Torque < 0Nm.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Brake_Axle_Wheel_TorqueFrictionMinimum {
    quantityReference = "ISQ::momentOfForce";
    unitReference = "SI::newtonMetre";
  }
  @VssRangeMetadata about Vehicle_MotionManagement_Brake_Axle_Wheel_TorqueFrictionMinimum {
    minValue = "";
    maxValue = "0";
  }

  attribute def Vehicle_MotionManagement_Brake_VehicleForceDistributionFrontMaximum :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Brake_VehicleForceDistributionFrontMaximum {
    path = "Vehicle.MotionManagement.Brake.VehicleForceDistributionFrontMaximum";
    kind = "actuator";
    datatype = "uint16";
    sourceDescription = "Maximum distribution range request of FxWhlSum to front axle. 0% = Complete longitudinal brake force shall be shifted to rear axle. 50% = At most 50% shall be shifted to front axle. 100% = Complete longitudinal brake force may be shifted to front axle.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Brake_VehicleForceDistributionFrontMaximum {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_MotionManagement_Brake_VehicleForceDistributionFrontMaximum {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_MotionManagement_Brake_VehicleForceDistributionFrontMinimum :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Brake_VehicleForceDistributionFrontMinimum {
    path = "Vehicle.MotionManagement.Brake.VehicleForceDistributionFrontMinimum";
    kind = "actuator";
    datatype = "uint16";
    sourceDescription = "Minimum distribution range request of FxWhlSum to front axle. 0% = Complete longitudinal brake force may be shifted to rear axle. 50% = At least 50% shall be shifted to front axle. 100% = Complete longitudinal brake force shall be shifted to front axle.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Brake_VehicleForceDistributionFrontMinimum {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_MotionManagement_Brake_VehicleForceDistributionFrontMinimum {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_MotionManagement_Brake_VehicleForceElectric :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Brake_VehicleForceElectric {
    path = "Vehicle.MotionManagement.Brake.VehicleForceElectric";
    kind = "actuator";
    datatype = "int16";
    sourceDescription = "Regenerative brake force request (FxWhlSum). Sum of all tyre longitudinal forces. Brake Force < 0N.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Brake_VehicleForceElectric {
    quantityReference = "ISQ::force";
    unitReference = "SI::newton";
  }
  @VssRangeMetadata about Vehicle_MotionManagement_Brake_VehicleForceElectric {
    minValue = "";
    maxValue = "0";
  }

  attribute def Vehicle_MotionManagement_Brake_VehicleForceElectricMinimumArbitrated :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Brake_VehicleForceElectricMinimumArbitrated {
    path = "Vehicle.MotionManagement.Brake.VehicleForceElectricMinimumArbitrated";
    kind = "sensor";
    datatype = "int16";
    sourceDescription = "Brake system internally calculated regenerative force limit at vehicle level for eAxle actuation. Brake Force < 0N.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Brake_VehicleForceElectricMinimumArbitrated {
    quantityReference = "ISQ::force";
    unitReference = "SI::newton";
  }
  @VssRangeMetadata about Vehicle_MotionManagement_Brake_VehicleForceElectricMinimumArbitrated {
    minValue = "";
    maxValue = "0";
  }

  attribute def Vehicle_MotionManagement_Brake_VehicleForceMaximum :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Brake_VehicleForceMaximum {
    path = "Vehicle.MotionManagement.Brake.VehicleForceMaximum";
    kind = "actuator";
    datatype = "int16";
    sourceDescription = "Maximum longitudinal brake force request (FxWhlSum). Sum of all tyre longitudinal forces. Brake Force < 0N.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Brake_VehicleForceMaximum {
    quantityReference = "ISQ::force";
    unitReference = "SI::newton";
  }
  @VssRangeMetadata about Vehicle_MotionManagement_Brake_VehicleForceMaximum {
    minValue = "";
    maxValue = "0";
  }

  attribute def Vehicle_MotionManagement_ElectricAxle_RotationalSpeed :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_ElectricAxle_RotationalSpeed {
    path = "Vehicle.MotionManagement.ElectricAxle.RotationalSpeed";
    kind = "sensor";
    datatype = "int16";
    sourceDescription = "Rotational speed for the specified axle, positive sign for rotation in forward direction, negative sign for rotation in backward direction.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_ElectricAxle_RotationalSpeed {
    quantityReference = "ISQ::angularVelocity";
    unitReference = "SI-derived revolutionPerMinute";
  }

  attribute def Vehicle_MotionManagement_ElectricAxle_RotationalSpeedMaximumLimit :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_ElectricAxle_RotationalSpeedMaximumLimit {
    path = "Vehicle.MotionManagement.ElectricAxle.RotationalSpeedMaximumLimit";
    kind = "actuator";
    datatype = "int16";
    sourceDescription = "Maximum allowed axle rotational speed in torque control mode, positive sign for rotation in forward direction, negative sign for rotation in backward direction.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_ElectricAxle_RotationalSpeedMaximumLimit {
    quantityReference = "ISQ::angularVelocity";
    unitReference = "SI-derived revolutionPerMinute";
  }

  attribute def Vehicle_MotionManagement_ElectricAxle_RotationalSpeedMinimumLimit :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_ElectricAxle_RotationalSpeedMinimumLimit {
    path = "Vehicle.MotionManagement.ElectricAxle.RotationalSpeedMinimumLimit";
    kind = "actuator";
    datatype = "int16";
    sourceDescription = "Minimum allowed axle rotational speed in torque control mode, positive sign for rotation in forward direction, negative sign for rotation in backward direction.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_ElectricAxle_RotationalSpeedMinimumLimit {
    quantityReference = "ISQ::angularVelocity";
    unitReference = "SI-derived revolutionPerMinute";
  }

  attribute def Vehicle_MotionManagement_ElectricAxle_RotationalSpeedTarget :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_ElectricAxle_RotationalSpeedTarget {
    path = "Vehicle.MotionManagement.ElectricAxle.RotationalSpeedTarget";
    kind = "actuator";
    datatype = "int16";
    sourceDescription = "Target axle rotational speed in rotation speed control mode, positive sign for rotation in forward direction, negative sign for rotation in backward direction.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_ElectricAxle_RotationalSpeedTarget {
    quantityReference = "ISQ::angularVelocity";
    unitReference = "SI-derived revolutionPerMinute";
  }

  attribute def Vehicle_MotionManagement_ElectricAxle_Torque :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_ElectricAxle_Torque {
    path = "Vehicle.MotionManagement.ElectricAxle.Torque";
    kind = "sensor";
    datatype = "int16";
    sourceDescription = "Axle torque, positive sign for torque in forward direction, negative sign for torque in backward direction.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_ElectricAxle_Torque {
    quantityReference = "ISQ::momentOfForce";
    unitReference = "SI::newtonMetre";
  }

  attribute def Vehicle_MotionManagement_ElectricAxle_TorqueMaximum :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_ElectricAxle_TorqueMaximum {
    path = "Vehicle.MotionManagement.ElectricAxle.TorqueMaximum";
    kind = "sensor";
    datatype = "int16";
    sourceDescription = "Maximum momentarily available eAxle torque, positive sign for torque in forward direction, negative sign for torque in backward direction.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_ElectricAxle_TorqueMaximum {
    quantityReference = "ISQ::momentOfForce";
    unitReference = "SI::newtonMetre";
  }

  attribute def Vehicle_MotionManagement_ElectricAxle_TorqueMaximumLimit :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_ElectricAxle_TorqueMaximumLimit {
    path = "Vehicle.MotionManagement.ElectricAxle.TorqueMaximumLimit";
    kind = "actuator";
    datatype = "int16";
    sourceDescription = "Maximum allowed eAxle torque in rotation speed control mode, positive sign for torque in forward direction, negative sign unused.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_ElectricAxle_TorqueMaximumLimit {
    quantityReference = "ISQ::momentOfForce";
    unitReference = "SI::newtonMetre";
  }

  attribute def Vehicle_MotionManagement_ElectricAxle_TorqueMinimum :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_ElectricAxle_TorqueMinimum {
    path = "Vehicle.MotionManagement.ElectricAxle.TorqueMinimum";
    kind = "sensor";
    datatype = "int16";
    sourceDescription = "Minimum momentarily available eAxle torque, positive sign for torque in forward direction, negative sign for torque in backward direction.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_ElectricAxle_TorqueMinimum {
    quantityReference = "ISQ::momentOfForce";
    unitReference = "SI::newtonMetre";
  }

  attribute def Vehicle_MotionManagement_ElectricAxle_TorqueMinimumLimit :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_ElectricAxle_TorqueMinimumLimit {
    path = "Vehicle.MotionManagement.ElectricAxle.TorqueMinimumLimit";
    kind = "actuator";
    datatype = "int16";
    sourceDescription = "Minimum allowed axle torque in rotation speed control mode, positive sign unused, negative sign for torque in backward direction (ISO8855).";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_ElectricAxle_TorqueMinimumLimit {
    quantityReference = "ISQ::momentOfForce";
    unitReference = "SI::newtonMetre";
  }

  attribute def Vehicle_MotionManagement_ElectricAxle_TorqueTarget :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_ElectricAxle_TorqueTarget {
    path = "Vehicle.MotionManagement.ElectricAxle.TorqueTarget";
    kind = "actuator";
    datatype = "int16";
    sourceDescription = "Target axle torque in torque control mode, positive sign for torque in forward direction, negative sign for torque in backward direction (ISO8855).";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_ElectricAxle_TorqueTarget {
    quantityReference = "ISQ::momentOfForce";
    unitReference = "SI::newtonMetre";
  }

  attribute def Vehicle_MotionManagement_Steering_Axle_Row1_PositionOffsetTargetMode :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Steering_Axle_Row1_PositionOffsetTargetMode {
    path = "Vehicle.MotionManagement.Steering.Axle.Row1.PositionOffsetTargetMode";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Mode used for controlling position offset interface of axle steering actuator. 0 indicates interface disabled. Other values activate vehicle specific modes.";
    sourceComment = "";
  }

  attribute def Vehicle_MotionManagement_Steering_Axle_Row1_PositionTargetMode :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Steering_Axle_Row1_PositionTargetMode {
    path = "Vehicle.MotionManagement.Steering.Axle.Row1.PositionTargetMode";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Mode used for controlling position interface of axle steering actuator. 0 indicates interface disabled. Other values activate vehicle specific modes.";
    sourceComment = "";
  }

  attribute def Vehicle_MotionManagement_Steering_Axle_Row1_RackPosition :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Steering_Axle_Row1_RackPosition {
    path = "Vehicle.MotionManagement.Steering.Axle.Row1.RackPosition";
    kind = "sensor";
    datatype = "int16";
    sourceDescription = "Represents the current position of the steering rack on axle steering actuator. Positive values leads to a left turn of the vehicle (based on ISO8855).";
    sourceComment = "Alternative signal to SteerAngle.";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Steering_Axle_Row1_RackPosition {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }

  attribute def Vehicle_MotionManagement_Steering_Axle_Row1_RackPositionOffsetTarget :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Steering_Axle_Row1_RackPositionOffsetTarget {
    path = "Vehicle.MotionManagement.Steering.Axle.Row1.RackPositionOffsetTarget";
    kind = "actuator";
    datatype = "int16";
    sourceDescription = "Rack position offset request to the axle steering actuator (for steer-by-wire), added to the actuator internal calculated set-point. Positive values without internal calculated set point change lead to a left movement of the vehicle (based on ISO8855).";
    sourceComment = "Alternative signal to SteerAngleOffsetTarget.";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Steering_Axle_Row1_RackPositionOffsetTarget {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }

  attribute def Vehicle_MotionManagement_Steering_Axle_Row1_RackPositionTarget :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Steering_Axle_Row1_RackPositionTarget {
    path = "Vehicle.MotionManagement.Steering.Axle.Row1.RackPositionTarget";
    kind = "actuator";
    datatype = "int16";
    sourceDescription = "Rack position request to the axle steering actuator (external set-point). Positive values lead to a left turn of the vehicle (based on ISO8855).";
    sourceComment = "Alternative signal to SteerAngleTarget.";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Steering_Axle_Row1_RackPositionTarget {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }

  attribute def Vehicle_MotionManagement_Steering_Axle_Row1_SteerAngle :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Steering_Axle_Row1_SteerAngle {
    path = "Vehicle.MotionManagement.Steering.Axle.Row1.SteerAngle";
    kind = "sensor";
    datatype = "int16";
    sourceDescription = "Represents the current actuated steering angle of the steered wheels. Signal orientation according ISO8855, single track model.";
    sourceComment = "Alternative signal to RackPosition.";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Steering_Axle_Row1_SteerAngle {
    quantityReference = "ISQ::planeAngle";
    unitReference = "SI::degree";
  }

  attribute def Vehicle_MotionManagement_Steering_Axle_Row1_SteerAngleOffsetTarget :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Steering_Axle_Row1_SteerAngleOffsetTarget {
    path = "Vehicle.MotionManagement.Steering.Axle.Row1.SteerAngleOffsetTarget";
    kind = "actuator";
    datatype = "int16";
    sourceDescription = "Steer angle offset request to the axle steering actuator (for steer-by-wire), added to the actuator internal calculated set-point. Signal orientation according ISO8855, single track model.";
    sourceComment = "Alternative signal to RackPositionOffsetTarget.";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Steering_Axle_Row1_SteerAngleOffsetTarget {
    quantityReference = "ISQ::planeAngle";
    unitReference = "SI::degree";
  }

  attribute def Vehicle_MotionManagement_Steering_Axle_Row1_SteerAngleTarget :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Steering_Axle_Row1_SteerAngleTarget {
    path = "Vehicle.MotionManagement.Steering.Axle.Row1.SteerAngleTarget";
    kind = "actuator";
    datatype = "int16";
    sourceDescription = "Steer angle request to the axle steering actuator (external set-point). Signal orientation according ISO8855, single track model.";
    sourceComment = "Alternative signal to RackPositionTarget.";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Steering_Axle_Row1_SteerAngleTarget {
    quantityReference = "ISQ::planeAngle";
    unitReference = "SI::degree";
  }

  attribute def Vehicle_MotionManagement_Steering_Axle_Row2_SteerAngle :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Steering_Axle_Row2_SteerAngle {
    path = "Vehicle.MotionManagement.Steering.Axle.Row2.SteerAngle";
    kind = "sensor";
    datatype = "int16";
    sourceDescription = "Represents the current actuated steering angle of the steered wheels on rear axle. Signal orientation according ISO8855, single track model.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Steering_Axle_Row2_SteerAngle {
    quantityReference = "ISQ::planeAngle";
    unitReference = "SI::degree";
  }

  attribute def Vehicle_MotionManagement_Steering_Axle_Row2_SteerAngleTarget :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Steering_Axle_Row2_SteerAngleTarget {
    path = "Vehicle.MotionManagement.Steering.Axle.Row2.SteerAngleTarget";
    kind = "actuator";
    datatype = "int16";
    sourceDescription = "Steer angle request to the rear axle steering actuator (external set-point). Signal orientation according ISO8855, single track model.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Steering_Axle_Row2_SteerAngleTarget {
    quantityReference = "ISQ::planeAngle";
    unitReference = "SI::degree";
  }

  attribute def Vehicle_MotionManagement_Steering_Axle_Row2_SteerAngleVelocityTarget :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Steering_Axle_Row2_SteerAngleVelocityTarget {
    path = "Vehicle.MotionManagement.Steering.Axle.Row2.SteerAngleVelocityTarget";
    kind = "actuator";
    datatype = "int16";
    sourceDescription = "Requested velocity for steer angle change. Signal orientation according ISO8855. Optional signal to adapt rear wheel steering closed loop control gain.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Steering_Axle_Row2_SteerAngleVelocityTarget {
    quantityReference = "ISQ::angularVelocity";
    unitReference = "SI::degreePerSecond";
  }

  attribute def Vehicle_MotionManagement_Steering_SteeringWheel_Angle :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Steering_SteeringWheel_Angle {
    path = "Vehicle.MotionManagement.Steering.SteeringWheel.Angle";
    kind = "sensor";
    datatype = "int16";
    sourceDescription = "Represents the current input angle of the steering system, typically corresponds to angle applied by driver on the steering-wheel. Positive for angle in counterclockwise direction (based on ISO8855).";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Steering_SteeringWheel_Angle {
    quantityReference = "ISQ::planeAngle";
    unitReference = "SI::degree";
  }

  attribute def Vehicle_MotionManagement_Steering_SteeringWheel_AngleTarget :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Steering_SteeringWheel_AngleTarget {
    path = "Vehicle.MotionManagement.Steering.SteeringWheel.AngleTarget";
    kind = "actuator";
    datatype = "int16";
    sourceDescription = "Steering-wheel angle request to the steering actuator (external set-point for steer-by-wire). Positive sign for angle in counterclockwise direction (based on ISO8855).";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Steering_SteeringWheel_AngleTarget {
    quantityReference = "ISQ::planeAngle";
    unitReference = "SI::degree";
  }

  attribute def Vehicle_MotionManagement_Steering_SteeringWheel_AngleTargetMode :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Steering_SteeringWheel_AngleTargetMode {
    path = "Vehicle.MotionManagement.Steering.SteeringWheel.AngleTargetMode";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Mode used for controlling Steering-wheel angle interface. 0 indicates interface disabled. Other values activate vehicle specific modes.";
    sourceComment = "";
  }

  attribute def Vehicle_MotionManagement_Steering_SteeringWheel_Torque :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Steering_SteeringWheel_Torque {
    path = "Vehicle.MotionManagement.Steering.SteeringWheel.Torque";
    kind = "sensor";
    datatype = "int16";
    sourceDescription = "Represents the current input torque for steering system, typically corresponds to torque applied by driver on the steering wheel. Positive for torque in counterclockwise direction (based on ISO8855).";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Steering_SteeringWheel_Torque {
    quantityReference = "ISQ::momentOfForce";
    unitReference = "SI::newtonMetre";
  }

  attribute def Vehicle_MotionManagement_Steering_SteeringWheel_TorqueOffsetTarget :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Steering_SteeringWheel_TorqueOffsetTarget {
    path = "Vehicle.MotionManagement.Steering.SteeringWheel.TorqueOffsetTarget";
    kind = "actuator";
    datatype = "int16";
    sourceDescription = "Steering-wheel torque offset request to the steering actuator, added to the actuator internal calculated target value. Positive sign for torque in counterclockwise direction (based on ISO8855).";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Steering_SteeringWheel_TorqueOffsetTarget {
    quantityReference = "ISQ::momentOfForce";
    unitReference = "SI::newtonMetre";
  }

  attribute def Vehicle_MotionManagement_Steering_SteeringWheel_TorqueOffsetTargetMode :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Steering_SteeringWheel_TorqueOffsetTargetMode {
    path = "Vehicle.MotionManagement.Steering.SteeringWheel.TorqueOffsetTargetMode";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Mode used for controlling steering-wheel torque offset interface. 0 indicates interface disabled. Other values activate vehicle specific modes.";
    sourceComment = "";
  }

  attribute def Vehicle_MotionManagement_Steering_SteeringWheel_TorqueTarget :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Steering_SteeringWheel_TorqueTarget {
    path = "Vehicle.MotionManagement.Steering.SteeringWheel.TorqueTarget";
    kind = "actuator";
    datatype = "int16";
    sourceDescription = "Steering-wheel torque request to the steering actuator (external set-point for steer-by-wire). Positive sign for torque in counterclockwise direction (based on ISO8855).";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Steering_SteeringWheel_TorqueTarget {
    quantityReference = "ISQ::momentOfForce";
    unitReference = "SI::newtonMetre";
  }

  attribute def Vehicle_MotionManagement_Steering_SteeringWheel_TorqueTargetMode :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Steering_SteeringWheel_TorqueTargetMode {
    path = "Vehicle.MotionManagement.Steering.SteeringWheel.TorqueTargetMode";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Mode used for controlling Steering-wheel torque interface. 0 indicates interface disabled. Other values activate vehicle specific modes.";
    sourceComment = "";
  }

  attribute def Vehicle_MotionManagement_Suspension_Axle_RollTorque :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Suspension_Axle_RollTorque {
    path = "Vehicle.MotionManagement.Suspension.Axle.RollTorque";
    kind = "sensor";
    datatype = "int16";
    sourceDescription = "Actuated roll torque on this axle by anti-roll actuator. Signal orientation according to ISO8855.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Suspension_Axle_RollTorque {
    quantityReference = "ISQ::momentOfForce";
    unitReference = "SI::newtonMetre";
  }

  attribute def Vehicle_MotionManagement_Suspension_Axle_Wheel_DampingForce :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Suspension_Axle_Wheel_DampingForce {
    path = "Vehicle.MotionManagement.Suspension.Axle.Wheel.DampingForce";
    kind = "sensor";
    datatype = "int16";
    sourceDescription = "Actuated damping force at given wheel. Signal orientation according ISO8855, meaning positive force is pointing upwards.";
    sourceComment = "Alternative signal to DampingRate.";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Suspension_Axle_Wheel_DampingForce {
    quantityReference = "ISQ::force";
    unitReference = "SI::newton";
  }

  attribute def Vehicle_MotionManagement_Suspension_Axle_Wheel_DampingForceTarget :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Suspension_Axle_Wheel_DampingForceTarget {
    path = "Vehicle.MotionManagement.Suspension.Axle.Wheel.DampingForceTarget";
    kind = "actuator";
    datatype = "int16";
    sourceDescription = "Damping force request at given wheel. Signal orientation according ISO8855, meaning positive force is pointing upwards.";
    sourceComment = "Alternative signal to DampingRateTarget.";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Suspension_Axle_Wheel_DampingForceTarget {
    quantityReference = "ISQ::force";
    unitReference = "SI::newton";
  }

  attribute def Vehicle_MotionManagement_Suspension_Axle_Wheel_DampingRate :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Suspension_Axle_Wheel_DampingRate {
    path = "Vehicle.MotionManagement.Suspension.Axle.Wheel.DampingRate";
    kind = "sensor";
    datatype = "uint8";
    sourceDescription = "Actuated damping rate at given wheel. 0% = lowest possible damping rate 100% = highest possible damping rate";
    sourceComment = "Alternative signal to DampingForce.";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Suspension_Axle_Wheel_DampingRate {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_MotionManagement_Suspension_Axle_Wheel_DampingRate {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_MotionManagement_Suspension_Axle_Wheel_DampingRateTarget :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Suspension_Axle_Wheel_DampingRateTarget {
    path = "Vehicle.MotionManagement.Suspension.Axle.Wheel.DampingRateTarget";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Damping rate request at given wheel. 0% = lowest possible damping rate 100% = highest possible damping rate";
    sourceComment = "Alternative signal to DampingForceTarget.";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Suspension_Axle_Wheel_DampingRateTarget {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_MotionManagement_Suspension_Axle_Wheel_DampingRateTarget {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_MotionManagement_Suspension_DampingPrioTarget :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Suspension_DampingPrioTarget {
    path = "Vehicle.MotionManagement.Suspension.DampingPrioTarget";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Prioritization target for damping control 0% = damping control by damping actuator (e.g. base functions) 100% = damping control by VMM system (e.g. vehicle dynamics)";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Suspension_DampingPrioTarget {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_MotionManagement_Suspension_DampingPrioTarget {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_MotionManagement_Suspension_RollPrioTarget :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Suspension_RollPrioTarget {
    path = "Vehicle.MotionManagement.Suspension.RollPrioTarget";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Prioritization target for anti-roll control 0% = anti-roll control by anti-roll actuator (e.g. base function) 100% = anti-roll control by VMM system (e.g. vehicle dynamics)";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Suspension_RollPrioTarget {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_MotionManagement_Suspension_RollPrioTarget {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_MotionManagement_Suspension_RollTorqueDistributionFrontMaximum :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Suspension_RollTorqueDistributionFrontMaximum {
    path = "Vehicle.MotionManagement.Suspension.RollTorqueDistributionFrontMaximum";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Maximum distribution range request of roll torque to front axle. 0% = Complete roll torque shall be shifted to rear axle 100% = Complete roll torque may be shifted to front axle";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Suspension_RollTorqueDistributionFrontMaximum {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_MotionManagement_Suspension_RollTorqueDistributionFrontMaximum {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_MotionManagement_Suspension_RollTorqueDistributionFrontMinimum :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Suspension_RollTorqueDistributionFrontMinimum {
    path = "Vehicle.MotionManagement.Suspension.RollTorqueDistributionFrontMinimum";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Minimum distribution range request of roll torque to front axle. 0% = Complete roll torque may be shifted to rear axle 100% = Complete roll torque shall be shifted to front axle";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Suspension_RollTorqueDistributionFrontMinimum {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_MotionManagement_Suspension_RollTorqueDistributionFrontMinimum {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_MotionManagement_Suspension_RollTorqueTarget :> Integer;
  @VssSignalMetadata about Vehicle_MotionManagement_Suspension_RollTorqueTarget {
    path = "Vehicle.MotionManagement.Suspension.RollTorqueTarget";
    kind = "actuator";
    datatype = "int16";
    sourceDescription = "Roll torque request on vehicle level. Signal orientation according to ISO8855.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_MotionManagement_Suspension_RollTorqueTarget {
    quantityReference = "ISQ::momentOfForce";
    unitReference = "SI::newtonMetre";
  }

  attribute def Vehicle_Occupant_HeadPosition_Pitch :> Real;
  @VssSignalMetadata about Vehicle_Occupant_HeadPosition_Pitch {
    path = "Vehicle.Occupant.HeadPosition.Pitch";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Head pitch angle, measured as angle from vehicle sprung mass XY-plane as defined by ISO 23150:2023 to the head X-axis. 0 = Head in normal position. Positive values = Head leaning up. Negative values = Head leaning down.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Occupant_HeadPosition_Pitch {
    quantityReference = "ISQ::planeAngle";
    unitReference = "SI::degree";
  }
  @VssRangeMetadata about Vehicle_Occupant_HeadPosition_Pitch {
    minValue = "-90";
    maxValue = "90";
  }

  attribute def Vehicle_Occupant_HeadPosition_Roll :> Real;
  @VssSignalMetadata about Vehicle_Occupant_HeadPosition_Roll {
    path = "Vehicle.Occupant.HeadPosition.Roll";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Head roll angle about the head X-axis (right-hand rule). 0 = Head in normal position. Positive values = Head leaning to the right. Negative values = Head leaning to the left.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Occupant_HeadPosition_Roll {
    quantityReference = "ISQ::planeAngle";
    unitReference = "SI::degree";
  }
  @VssRangeMetadata about Vehicle_Occupant_HeadPosition_Roll {
    minValue = "-180";
    maxValue = "180";
  }

  attribute def Vehicle_Occupant_HeadPosition_X :> Integer;
  @VssSignalMetadata about Vehicle_Occupant_HeadPosition_X {
    path = "Vehicle.Occupant.HeadPosition.X";
    kind = "sensor";
    datatype = "int16";
    sourceDescription = "Longitudinal position of head center measured as mid eye position on X-axis of the vehicle rear-axle coordinate system as defined by ISO 23150:2023 section 3.7.12 Mid eye position refers to the center of a line drawn between the center of the drivers eyes. Positive values = forward of (first) rear-axle. Negative values = backward of (first) rear-axle.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Occupant_HeadPosition_X {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }

  attribute def Vehicle_Occupant_HeadPosition_Y :> Integer;
  @VssSignalMetadata about Vehicle_Occupant_HeadPosition_Y {
    path = "Vehicle.Occupant.HeadPosition.Y";
    kind = "sensor";
    datatype = "int16";
    sourceDescription = "Lateral position of head center measured as mid eye position on X-axis of the vehicle rear-axle coordinate system as defined by ISO 23150:2023 section 3.7.12 Mid eye position refers to the center of a line drawn between the center of the drivers eyes. Positive values = left of rear-axle center. Negative values = right of rear-axle center.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Occupant_HeadPosition_Y {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }

  attribute def Vehicle_Occupant_HeadPosition_Yaw :> Real;
  @VssSignalMetadata about Vehicle_Occupant_HeadPosition_Yaw {
    path = "Vehicle.Occupant.HeadPosition.Yaw";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Head yaw angle, measured from the vehicle sprung mass X-axis as defined by ISO 23150:2023 to the head X-axis, around the vehicle Z-axis (right-hand rule). 0 = Head in normal position. Positive values = Head turned left. Negative values = Head turned right.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Occupant_HeadPosition_Yaw {
    quantityReference = "ISQ::planeAngle";
    unitReference = "SI::degree";
  }
  @VssRangeMetadata about Vehicle_Occupant_HeadPosition_Yaw {
    minValue = "-180";
    maxValue = "180";
  }

  attribute def Vehicle_Occupant_HeadPosition_Z :> Integer;
  @VssSignalMetadata about Vehicle_Occupant_HeadPosition_Z {
    path = "Vehicle.Occupant.HeadPosition.Z";
    kind = "sensor";
    datatype = "int16";
    sourceDescription = "Height position of head center measured as mid eye position on X-axis of the vehicle rear-axle coordinate system as defined by ISO 23150:2023 section 3.7.12 Mid eye position refers to the center of a line drawn between the center of the drivers eyes. Positive values = above center of rear-axle reference point. Negative values = below center of rear-axle reference point.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Occupant_HeadPosition_Z {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }

  attribute def Vehicle_Occupant_Identifier_Issuer :> String;
  @VssSignalMetadata about Vehicle_Occupant_Identifier_Issuer {
    path = "Vehicle.Occupant.Identifier.Issuer";
    kind = "sensor";
    datatype = "string";
    sourceDescription = "Unique Issuer for the authentication of the occupant e.g. https://accounts.funcorp.com.";
    sourceComment = "";
  }

  attribute def Vehicle_Occupant_Identifier_Subject :> String;
  @VssSignalMetadata about Vehicle_Occupant_Identifier_Subject {
    path = "Vehicle.Occupant.Identifier.Subject";
    kind = "sensor";
    datatype = "string";
    sourceDescription = "Subject for the authentication of the occupant e.g. UserID 7331677.";
    sourceComment = "";
  }

  attribute def Vehicle_Occupant_MidEyeGaze_Azimuth :> Real;
  @VssSignalMetadata about Vehicle_Occupant_MidEyeGaze_Azimuth {
    path = "Vehicle.Occupant.MidEyeGaze.Azimuth";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Mid eye azimuth gaze (right-hand rule) on vehicle sprung mass Z-axis as defined by ISO 23150:2023 0 = Driver looking forward. Positive values = Driver looking at something on the left side of driver. Negative values = Driver looking at something on the right side of driver.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Occupant_MidEyeGaze_Azimuth {
    quantityReference = "ISQ::planeAngle";
    unitReference = "SI::degree";
  }
  @VssRangeMetadata about Vehicle_Occupant_MidEyeGaze_Azimuth {
    minValue = "-180";
    maxValue = "180";
  }

  attribute def Vehicle_Occupant_MidEyeGaze_Elevation :> Real;
  @VssSignalMetadata about Vehicle_Occupant_MidEyeGaze_Elevation {
    path = "Vehicle.Occupant.MidEyeGaze.Elevation";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Elevation to observed object measured as angle between vehicle sprung mass XY-plane as defined by ISO 23150:2023 at driver mid eye position and object. 0 = Driver looking at something at same height as mid eye position. Positive values = Driver looking at something above mid eye position. Negative values = Driver looking at something below mid eye position.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Occupant_MidEyeGaze_Elevation {
    quantityReference = "ISQ::planeAngle";
    unitReference = "SI::degree";
  }
  @VssRangeMetadata about Vehicle_Occupant_MidEyeGaze_Elevation {
    minValue = "-90";
    maxValue = "90";
  }

  attribute def Vehicle_PowerOptimizeLevel :> Integer;
  @VssSignalMetadata about Vehicle_PowerOptimizeLevel {
    path = "Vehicle.PowerOptimizeLevel";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Power optimization level for this branch/subsystem. A higher number indicates more aggressive power optimization. Level 0 indicates that all functionality is enabled, no power optimization enabled. Level 10 indicates most aggressive power optimization mode, only essential functionality enabled.";
    sourceComment = "";
  }
  @VssRangeMetadata about Vehicle_PowerOptimizeLevel {
    minValue = "0";
    maxValue = "10";
  }

  attribute def Vehicle_Powertrain_AccumulatedBrakingEnergy :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_AccumulatedBrakingEnergy {
    path = "Vehicle.Powertrain.AccumulatedBrakingEnergy";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "The accumulated energy from regenerative braking over lifetime.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_AccumulatedBrakingEnergy {
    quantityReference = "ISQ::energy";
    unitReference = "SI::kilowattHour";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_AspirationType :> Vehicle_Powertrain_CombustionEngine_AspirationType_AllowedValue;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_AspirationType {
    path = "Vehicle.Powertrain.CombustionEngine.AspirationType";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "Type of aspiration (natural, turbocharger, supercharger etc).";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Powertrain_CombustionEngine_AspirationType {
    allowedValues = "UNKNOWN, NATURAL, SUPERCHARGER, TURBOCHARGER";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_Bore :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_Bore {
    path = "Vehicle.Powertrain.CombustionEngine.Bore";
    kind = "attribute";
    datatype = "float";
    sourceDescription = "Bore in millimetres.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_CombustionEngine_Bore {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_CompressionRatio :> String;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_CompressionRatio {
    path = "Vehicle.Powertrain.CombustionEngine.CompressionRatio";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "Engine compression ratio, specified in the format 'X:1', e.g. '9.2:1'.";
    sourceComment = "";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_Configuration :> Vehicle_Powertrain_CombustionEngine_Configuration_AllowedValue;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_Configuration {
    path = "Vehicle.Powertrain.CombustionEngine.Configuration";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "Engine configuration.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Powertrain_CombustionEngine_Configuration {
    allowedValues = "UNKNOWN, STRAIGHT, V, BOXER, W, ROTARY, RADIAL, SQUARE, H, U, OPPOSED, X";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_DieselExhaustFluid_Capacity :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_DieselExhaustFluid_Capacity {
    path = "Vehicle.Powertrain.CombustionEngine.DieselExhaustFluid.Capacity";
    kind = "attribute";
    datatype = "float";
    sourceDescription = "Capacity in liters of the Diesel Exhaust Fluid Tank.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_CombustionEngine_DieselExhaustFluid_Capacity {
    quantityReference = "ISQ::volume";
    unitReference = "SI::litre";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_DieselExhaustFluid_IsLevelLow :> Boolean;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_DieselExhaustFluid_IsLevelLow {
    path = "Vehicle.Powertrain.CombustionEngine.DieselExhaustFluid.IsLevelLow";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if the Diesel Exhaust Fluid level is low. True if level is low. Definition of low is vehicle dependent.";
    sourceComment = "";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_DieselExhaustFluid_Level :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_DieselExhaustFluid_Level {
    path = "Vehicle.Powertrain.CombustionEngine.DieselExhaustFluid.Level";
    kind = "sensor";
    datatype = "uint8";
    sourceDescription = "Level of the Diesel Exhaust Fluid tank as percent of capacity. 0 = empty. 100 = full.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_CombustionEngine_DieselExhaustFluid_Level {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Powertrain_CombustionEngine_DieselExhaustFluid_Level {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_DieselExhaustFluid_Range :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_DieselExhaustFluid_Range {
    path = "Vehicle.Powertrain.CombustionEngine.DieselExhaustFluid.Range";
    kind = "sensor";
    datatype = "uint32";
    sourceDescription = "Remaining range in meters of the Diesel Exhaust Fluid present in the vehicle.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_CombustionEngine_DieselExhaustFluid_Range {
    quantityReference = "ISQ::length";
    unitReference = "SI::metre";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_DieselParticulateFilter_DeltaPressure :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_DieselParticulateFilter_DeltaPressure {
    path = "Vehicle.Powertrain.CombustionEngine.DieselParticulateFilter.DeltaPressure";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Delta Pressure of Diesel Particulate Filter.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_CombustionEngine_DieselParticulateFilter_DeltaPressure {
    quantityReference = "ISQ::pressure";
    unitReference = "SI::pascal";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_DieselParticulateFilter_InletTemperature :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_DieselParticulateFilter_InletTemperature {
    path = "Vehicle.Powertrain.CombustionEngine.DieselParticulateFilter.InletTemperature";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Inlet temperature of Diesel Particulate Filter.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_CombustionEngine_DieselParticulateFilter_InletTemperature {
    quantityReference = "ISQ::thermodynamicTemperature";
    unitReference = "SI::degreeCelsius";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_DieselParticulateFilter_OutletTemperature :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_DieselParticulateFilter_OutletTemperature {
    path = "Vehicle.Powertrain.CombustionEngine.DieselParticulateFilter.OutletTemperature";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Outlet temperature of Diesel Particulate Filter.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_CombustionEngine_DieselParticulateFilter_OutletTemperature {
    quantityReference = "ISQ::thermodynamicTemperature";
    unitReference = "SI::degreeCelsius";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_Displacement :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_Displacement {
    path = "Vehicle.Powertrain.CombustionEngine.Displacement";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Displacement in cubic centimetres.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_CombustionEngine_Displacement {
    quantityReference = "ISQ::volume";
    unitReference = "SI::cubicCentimetre";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_EOP :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_EOP {
    path = "Vehicle.Powertrain.CombustionEngine.EOP";
    kind = "sensor";
    datatype = "uint16";
    sourceDescription = "Engine oil pressure.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_CombustionEngine_EOP {
    quantityReference = "ISQ::pressure";
    unitReference = "SI::kilopascal";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_EngineCode :> String;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_EngineCode {
    path = "Vehicle.Powertrain.CombustionEngine.EngineCode";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "Engine code designation, as specified by vehicle manufacturer.";
    sourceComment = "For hybrid vehicles the engine code may refer to the combination of combustion and electric engine.";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_EngineCoolant_Capacity :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_EngineCoolant_Capacity {
    path = "Vehicle.Powertrain.CombustionEngine.EngineCoolant.Capacity";
    kind = "attribute";
    datatype = "float";
    sourceDescription = "Engine coolant capacity in liters.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_CombustionEngine_EngineCoolant_Capacity {
    quantityReference = "ISQ::volume";
    unitReference = "SI::litre";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_EngineCoolant_Level :> Vehicle_Powertrain_CombustionEngine_EngineCoolant_Level_AllowedValue;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_EngineCoolant_Level {
    path = "Vehicle.Powertrain.CombustionEngine.EngineCoolant.Level";
    kind = "sensor";
    datatype = "string";
    sourceDescription = "Engine coolant level.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Powertrain_CombustionEngine_EngineCoolant_Level {
    allowedValues = "CRITICALLY_LOW, LOW, NORMAL";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_EngineCoolant_LifeRemaining :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_EngineCoolant_LifeRemaining {
    path = "Vehicle.Powertrain.CombustionEngine.EngineCoolant.LifeRemaining";
    kind = "sensor";
    datatype = "int32";
    sourceDescription = "Remaining engine coolant life in seconds. Negative values can be used to indicate that lifetime has been exceeded.";
    sourceComment = "In addition to this a signal a vehicle can report remaining time to service (including e.g. coolant change) by Vehicle.Service.TimeToService.";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_CombustionEngine_EngineCoolant_LifeRemaining {
    quantityReference = "ISQ::time";
    unitReference = "SI::second";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_EngineCoolant_Temperature :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_EngineCoolant_Temperature {
    path = "Vehicle.Powertrain.CombustionEngine.EngineCoolant.Temperature";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Engine coolant temperature.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_CombustionEngine_EngineCoolant_Temperature {
    quantityReference = "ISQ::thermodynamicTemperature";
    unitReference = "SI::degreeCelsius";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_EngineHours :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_EngineHours {
    path = "Vehicle.Powertrain.CombustionEngine.EngineHours";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Accumulated time during engine lifetime with 'engine speed (rpm) > 0'.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_CombustionEngine_EngineHours {
    quantityReference = "ISQ::time";
    unitReference = "SI::hour";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_EngineOil_Capacity :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_EngineOil_Capacity {
    path = "Vehicle.Powertrain.CombustionEngine.EngineOil.Capacity";
    kind = "attribute";
    datatype = "float";
    sourceDescription = "Engine oil capacity in liters.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_CombustionEngine_EngineOil_Capacity {
    quantityReference = "ISQ::volume";
    unitReference = "SI::litre";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_EngineOil_Level :> Vehicle_Powertrain_CombustionEngine_EngineOil_Level_AllowedValue;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_EngineOil_Level {
    path = "Vehicle.Powertrain.CombustionEngine.EngineOil.Level";
    kind = "sensor";
    datatype = "string";
    sourceDescription = "Engine oil level.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Powertrain_CombustionEngine_EngineOil_Level {
    allowedValues = "CRITICALLY_LOW, LOW, NORMAL, HIGH, CRITICALLY_HIGH";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_EngineOil_LifeRemaining :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_EngineOil_LifeRemaining {
    path = "Vehicle.Powertrain.CombustionEngine.EngineOil.LifeRemaining";
    kind = "sensor";
    datatype = "int32";
    sourceDescription = "Remaining engine oil life in seconds. Negative values can be used to indicate that lifetime has been exceeded.";
    sourceComment = "In addition to this a signal a vehicle can report remaining time to service (including e.g. oil change) by Vehicle.Service.TimeToService.";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_CombustionEngine_EngineOil_LifeRemaining {
    quantityReference = "ISQ::time";
    unitReference = "SI::second";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_EngineOil_Temperature :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_EngineOil_Temperature {
    path = "Vehicle.Powertrain.CombustionEngine.EngineOil.Temperature";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "EOT, Engine oil temperature.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_CombustionEngine_EngineOil_Temperature {
    quantityReference = "ISQ::thermodynamicTemperature";
    unitReference = "SI::degreeCelsius";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_IdleHours :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_IdleHours {
    path = "Vehicle.Powertrain.CombustionEngine.IdleHours";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Accumulated idling time during engine lifetime. Definition of idling is not standardized.";
    sourceComment = "Vehicles may calculate accumulated idle time for an engine. It might be based on engine speed (rpm) below a certain limit or any other mechanism.";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_CombustionEngine_IdleHours {
    quantityReference = "ISQ::time";
    unitReference = "SI::hour";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_IsRunning :> Boolean;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_IsRunning {
    path = "Vehicle.Powertrain.CombustionEngine.IsRunning";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Engine Running. True if engine is rotating (Speed > 0).";
    sourceComment = "";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_MAF :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_MAF {
    path = "Vehicle.Powertrain.CombustionEngine.MAF";
    kind = "sensor";
    datatype = "uint16";
    sourceDescription = "Grams of air drawn into engine per second.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_CombustionEngine_MAF {
    quantityReference = "ISQ::massFlowRate";
    unitReference = "SI::gramPerSecond";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_MAP :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_MAP {
    path = "Vehicle.Powertrain.CombustionEngine.MAP";
    kind = "sensor";
    datatype = "uint16";
    sourceDescription = "Manifold absolute pressure possibly boosted using forced induction.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_CombustionEngine_MAP {
    quantityReference = "ISQ::pressure";
    unitReference = "SI::kilopascal";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_MaxPower :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_MaxPower {
    path = "Vehicle.Powertrain.CombustionEngine.MaxPower";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Peak power, in kilowatts, that engine can generate.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_CombustionEngine_MaxPower {
    quantityReference = "ISQ::power";
    unitReference = "SI::kilowatt";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_MaxTorque :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_MaxTorque {
    path = "Vehicle.Powertrain.CombustionEngine.MaxTorque";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Peak torque, in newton meter, that the engine can generate.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_CombustionEngine_MaxTorque {
    quantityReference = "ISQ::momentOfForce";
    unitReference = "SI::newtonMetre";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_NumberOfCylinders :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_NumberOfCylinders {
    path = "Vehicle.Powertrain.CombustionEngine.NumberOfCylinders";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Number of cylinders.";
    sourceComment = "";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_NumberOfValvesPerCylinder :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_NumberOfValvesPerCylinder {
    path = "Vehicle.Powertrain.CombustionEngine.NumberOfValvesPerCylinder";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Number of valves per cylinder.";
    sourceComment = "";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_Power :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_Power {
    path = "Vehicle.Powertrain.CombustionEngine.Power";
    kind = "sensor";
    datatype = "uint16";
    sourceDescription = "Current engine power output. Shall be reported as 0 during engine breaking.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_CombustionEngine_Power {
    quantityReference = "ISQ::power";
    unitReference = "SI::kilowatt";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_Speed :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_Speed {
    path = "Vehicle.Powertrain.CombustionEngine.Speed";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Engine speed measured as rotations per minute.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_CombustionEngine_Speed {
    quantityReference = "ISQ::angularVelocity";
    unitReference = "SI-derived revolutionPerMinute";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_StrokeLength :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_StrokeLength {
    path = "Vehicle.Powertrain.CombustionEngine.StrokeLength";
    kind = "attribute";
    datatype = "float";
    sourceDescription = "Stroke length in millimetres.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_CombustionEngine_StrokeLength {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_TPS :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_TPS {
    path = "Vehicle.Powertrain.CombustionEngine.TPS";
    kind = "sensor";
    datatype = "uint8";
    sourceDescription = "Current throttle position.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_CombustionEngine_TPS {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Powertrain_CombustionEngine_TPS {
    minValue = "";
    maxValue = "100";
  }

  attribute def Vehicle_Powertrain_CombustionEngine_Torque :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_CombustionEngine_Torque {
    path = "Vehicle.Powertrain.CombustionEngine.Torque";
    kind = "sensor";
    datatype = "int16";
    sourceDescription = "Current engine torque. Shall be reported as a negative number during engine breaking.";
    sourceComment = "During engine breaking the engine delivers a negative torque to the transmission.";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_CombustionEngine_Torque {
    quantityReference = "ISQ::momentOfForce";
    unitReference = "SI::newtonMetre";
  }

  attribute def Vehicle_Powertrain_ElectricMotor_EngineCode :> String;
  @VssSignalMetadata about Vehicle_Powertrain_ElectricMotor_EngineCode {
    path = "Vehicle.Powertrain.ElectricMotor.EngineCode";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "Engine code designation, as specified by vehicle manufacturer.";
    sourceComment = "";
  }

  attribute def Vehicle_Powertrain_ElectricMotor_EngineCoolant_Capacity :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_ElectricMotor_EngineCoolant_Capacity {
    path = "Vehicle.Powertrain.ElectricMotor.EngineCoolant.Capacity";
    kind = "attribute";
    datatype = "float";
    sourceDescription = "Engine coolant capacity in liters.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_ElectricMotor_EngineCoolant_Capacity {
    quantityReference = "ISQ::volume";
    unitReference = "SI::litre";
  }

  attribute def Vehicle_Powertrain_ElectricMotor_EngineCoolant_Level :> Vehicle_Powertrain_ElectricMotor_EngineCoolant_Level_AllowedValue;
  @VssSignalMetadata about Vehicle_Powertrain_ElectricMotor_EngineCoolant_Level {
    path = "Vehicle.Powertrain.ElectricMotor.EngineCoolant.Level";
    kind = "sensor";
    datatype = "string";
    sourceDescription = "Engine coolant level.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Powertrain_ElectricMotor_EngineCoolant_Level {
    allowedValues = "CRITICALLY_LOW, LOW, NORMAL";
  }

  attribute def Vehicle_Powertrain_ElectricMotor_EngineCoolant_LifeRemaining :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_ElectricMotor_EngineCoolant_LifeRemaining {
    path = "Vehicle.Powertrain.ElectricMotor.EngineCoolant.LifeRemaining";
    kind = "sensor";
    datatype = "int32";
    sourceDescription = "Remaining engine coolant life in seconds. Negative values can be used to indicate that lifetime has been exceeded.";
    sourceComment = "In addition to this a signal a vehicle can report remaining time to service (including e.g. coolant change) by Vehicle.Service.TimeToService.";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_ElectricMotor_EngineCoolant_LifeRemaining {
    quantityReference = "ISQ::time";
    unitReference = "SI::second";
  }

  attribute def Vehicle_Powertrain_ElectricMotor_EngineCoolant_Temperature :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_ElectricMotor_EngineCoolant_Temperature {
    path = "Vehicle.Powertrain.ElectricMotor.EngineCoolant.Temperature";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Engine coolant temperature.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_ElectricMotor_EngineCoolant_Temperature {
    quantityReference = "ISQ::thermodynamicTemperature";
    unitReference = "SI::degreeCelsius";
  }

  attribute def Vehicle_Powertrain_ElectricMotor_MaxPower :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_ElectricMotor_MaxPower {
    path = "Vehicle.Powertrain.ElectricMotor.MaxPower";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Peak power, in kilowatts, that motor(s) can generate.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_ElectricMotor_MaxPower {
    quantityReference = "ISQ::power";
    unitReference = "SI::kilowatt";
  }

  attribute def Vehicle_Powertrain_ElectricMotor_MaxRegenPower :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_ElectricMotor_MaxRegenPower {
    path = "Vehicle.Powertrain.ElectricMotor.MaxRegenPower";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Peak regen/brake power, in kilowatts, that motor(s) can generate.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_ElectricMotor_MaxRegenPower {
    quantityReference = "ISQ::power";
    unitReference = "SI::kilowatt";
  }

  attribute def Vehicle_Powertrain_ElectricMotor_MaxRegenTorque :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_ElectricMotor_MaxRegenTorque {
    path = "Vehicle.Powertrain.ElectricMotor.MaxRegenTorque";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Peak regen/brake torque, in newton meter, that the motor(s) can generate.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_ElectricMotor_MaxRegenTorque {
    quantityReference = "ISQ::momentOfForce";
    unitReference = "SI::newtonMetre";
  }

  attribute def Vehicle_Powertrain_ElectricMotor_MaxTorque :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_ElectricMotor_MaxTorque {
    path = "Vehicle.Powertrain.ElectricMotor.MaxTorque";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Peak power, in newton meter, that the motor(s) can generate.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_ElectricMotor_MaxTorque {
    quantityReference = "ISQ::momentOfForce";
    unitReference = "SI::newtonMetre";
  }

  attribute def Vehicle_Powertrain_ElectricMotor_Power :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_ElectricMotor_Power {
    path = "Vehicle.Powertrain.ElectricMotor.Power";
    kind = "sensor";
    datatype = "int16";
    sourceDescription = "Current motor power output. Negative values indicate regen mode.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_ElectricMotor_Power {
    quantityReference = "ISQ::power";
    unitReference = "SI::kilowatt";
  }

  attribute def Vehicle_Powertrain_ElectricMotor_Speed :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_ElectricMotor_Speed {
    path = "Vehicle.Powertrain.ElectricMotor.Speed";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Motor rotational speed measured as rotations per minute. Negative values indicate reverse driving mode.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_ElectricMotor_Speed {
    quantityReference = "ISQ::angularVelocity";
    unitReference = "SI-derived revolutionPerMinute";
  }

  attribute def Vehicle_Powertrain_ElectricMotor_Temperature :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_ElectricMotor_Temperature {
    path = "Vehicle.Powertrain.ElectricMotor.Temperature";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Motor temperature.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_ElectricMotor_Temperature {
    quantityReference = "ISQ::thermodynamicTemperature";
    unitReference = "SI::degreeCelsius";
  }

  attribute def Vehicle_Powertrain_ElectricMotor_TimeInUse :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_ElectricMotor_TimeInUse {
    path = "Vehicle.Powertrain.ElectricMotor.TimeInUse";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Accumulated time during engine lifetime when the vehicule state's is 'READY'.";
    sourceComment = "Vehicles may define their READY state.";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_ElectricMotor_TimeInUse {
    quantityReference = "ISQ::time";
    unitReference = "SI::hour";
  }

  attribute def Vehicle_Powertrain_ElectricMotor_Torque :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_ElectricMotor_Torque {
    path = "Vehicle.Powertrain.ElectricMotor.Torque";
    kind = "sensor";
    datatype = "int16";
    sourceDescription = "Current motor torque. Negative values indicate regen mode.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_ElectricMotor_Torque {
    quantityReference = "ISQ::momentOfForce";
    unitReference = "SI::newtonMetre";
  }

  attribute def Vehicle_Powertrain_FuelSystem_AbsoluteLevel :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_FuelSystem_AbsoluteLevel {
    path = "Vehicle.Powertrain.FuelSystem.AbsoluteLevel";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Current available fuel in the fuel tank expressed in liters.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_FuelSystem_AbsoluteLevel {
    quantityReference = "ISQ::volume";
    unitReference = "SI::litre";
  }

  attribute def Vehicle_Powertrain_FuelSystem_AfterRefuelingFuelEconomy :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_FuelSystem_AfterRefuelingFuelEconomy {
    path = "Vehicle.Powertrain.FuelSystem.AfterRefuelingFuelEconomy";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Average fuel economy calculated from the most recent refueling event to the current time.";
    sourceComment = "This value represents the fuel efficiency for the period between consecutive refueling events. It is automatically reset to zero when refueling is detected and begins accumulating from that point. The calculation continues until the next refueling occurs. This metric is useful for tracking fuel efficiency improvements or changes between fill-ups.";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_FuelSystem_AfterRefuelingFuelEconomy {
    quantityReference = "ISQ::fuelEfficiency";
    unitReference = "SI-derived kilometre/litre";
  }

  attribute def Vehicle_Powertrain_FuelSystem_AverageConsumption :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_FuelSystem_AverageConsumption {
    path = "Vehicle.Powertrain.FuelSystem.AverageConsumption";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Average consumption in liters per 100 km.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_FuelSystem_AverageConsumption {
    quantityReference = "ISQ::fuelConsumption";
    unitReference = "SI-derived litrePer100Kilometre";
  }
  @VssRangeMetadata about Vehicle_Powertrain_FuelSystem_AverageConsumption {
    minValue = "0";
    maxValue = "";
  }

  attribute def Vehicle_Powertrain_FuelSystem_ConsumptionSinceLastRefuel :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_FuelSystem_ConsumptionSinceLastRefuel {
    path = "Vehicle.Powertrain.FuelSystem.ConsumptionSinceLastRefuel";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Fuel consumption since last refueling.";
    sourceComment = "Amount of fuel consumed since last refueling.";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_FuelSystem_ConsumptionSinceLastRefuel {
    quantityReference = "ISQ::volume";
    unitReference = "SI::litre";
  }

  attribute def Vehicle_Powertrain_FuelSystem_ConsumptionSinceStart :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_FuelSystem_ConsumptionSinceStart {
    path = "Vehicle.Powertrain.FuelSystem.ConsumptionSinceStart";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Fuel amount in liters consumed since start of current trip.";
    sourceComment = "A new trip is considered to start when engine gets enabled (e.g. LowVoltageSystemState in ON or START mode). A trip is considered to end when engine is no longer enabled. The signal may however keep the value of the last trip until a new trip is started.";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_FuelSystem_ConsumptionSinceStart {
    quantityReference = "ISQ::volume";
    unitReference = "SI::litre";
  }

  attribute def Vehicle_Powertrain_FuelSystem_CumulativeFuelEconomy :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_FuelSystem_CumulativeFuelEconomy {
    path = "Vehicle.Powertrain.FuelSystem.CumulativeFuelEconomy";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Cumulative average fuel economy calculated from vehicle start or last user reset.";
    sourceComment = "This represents the accumulated fuel economy over the entire period since the last reset. Unlike trip-based measurements, this provides a long-term average of fuel efficiency.";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_FuelSystem_CumulativeFuelEconomy {
    quantityReference = "ISQ::fuelEfficiency";
    unitReference = "SI-derived kilometre/litre";
  }

  attribute def Vehicle_Powertrain_FuelSystem_DriveFuelEconomy :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_FuelSystem_DriveFuelEconomy {
    path = "Vehicle.Powertrain.FuelSystem.DriveFuelEconomy";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Average fuel economy for the current drive cycle, calculated from engine start to current time.";
    sourceComment = "This represents the fuel efficiency during the active driving session. The value is reset when the engine is no longer enabled or when the user manually initiates a drive fuel economy reset. After reset, it is recalculated from zero when the engine restarts or the new drive cycle begins. It provides real-time average fuel economy for the ongoing drive cycle.";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_FuelSystem_DriveFuelEconomy {
    quantityReference = "ISQ::fuelEfficiency";
    unitReference = "SI-derived kilometre/litre";
  }

  attribute def Vehicle_Powertrain_FuelSystem_HybridType :> Vehicle_Powertrain_FuelSystem_HybridType_AllowedValue;
  @VssSignalMetadata about Vehicle_Powertrain_FuelSystem_HybridType {
    path = "Vehicle.Powertrain.FuelSystem.HybridType";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "Defines the hybrid type of the vehicle.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Powertrain_FuelSystem_HybridType {
    allowedValues = "UNKNOWN, NOT_APPLICABLE, STOP_START, BELT_ISG, CIMG, PHEV";
  }

  attribute def Vehicle_Powertrain_FuelSystem_InstantConsumption :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_FuelSystem_InstantConsumption {
    path = "Vehicle.Powertrain.FuelSystem.InstantConsumption";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Current consumption in liters per 100 km.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_FuelSystem_InstantConsumption {
    quantityReference = "ISQ::fuelConsumption";
    unitReference = "SI-derived litrePer100Kilometre";
  }
  @VssRangeMetadata about Vehicle_Powertrain_FuelSystem_InstantConsumption {
    minValue = "0";
    maxValue = "";
  }

  attribute def Vehicle_Powertrain_FuelSystem_InstantantFuelEconomy :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_FuelSystem_InstantantFuelEconomy {
    path = "Vehicle.Powertrain.FuelSystem.InstantantFuelEconomy";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Real-time instantaneous fuel economy calculated over a short time window.";
    sourceComment = "This value represents the current fuel efficiency at any given moment during vehicle operation. It is calculated based on the distance traveled and fuel consumed over a brief sampling period (typically around 500ms). The calculation compares the vehicle state before and after the sampling window to determine instantaneous efficiency. This metric refreshes frequently and can fluctuate significantly based on driving conditions, acceleration, and terrain. Unlike average fuel economy measurements, this provides immediate feedback on current driving efficiency.";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_FuelSystem_InstantantFuelEconomy {
    quantityReference = "ISQ::fuelEfficiency";
    unitReference = "SI-derived kilometre/litre";
  }

  attribute def Vehicle_Powertrain_FuelSystem_IsEngineStopStartEnabled :> Boolean;
  @VssSignalMetadata about Vehicle_Powertrain_FuelSystem_IsEngineStopStartEnabled {
    path = "Vehicle.Powertrain.FuelSystem.IsEngineStopStartEnabled";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates whether eco start stop is currently enabled.";
    sourceComment = "";
  }

  attribute def Vehicle_Powertrain_FuelSystem_IsFuelLevelEmpty :> Boolean;
  @VssSignalMetadata about Vehicle_Powertrain_FuelSystem_IsFuelLevelEmpty {
    path = "Vehicle.Powertrain.FuelSystem.IsFuelLevelEmpty";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates that the fuel gauge on the instrument cluster displays empty (0).";
    sourceComment = "When this signal is true, the fuel gauge displays empty (0), but the vehicle typically still has reserve fuel allowing for some additional driving range depending on the vehicle design. This represents the displayed empty state, not actual tank empty condition.";
  }

  attribute def Vehicle_Powertrain_FuelSystem_IsFuelLevelLow :> Boolean;
  @VssSignalMetadata about Vehicle_Powertrain_FuelSystem_IsFuelLevelLow {
    path = "Vehicle.Powertrain.FuelSystem.IsFuelLevelLow";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates that the fuel level is low (e.g. <50km range).";
    sourceComment = "";
  }

  attribute def Vehicle_Powertrain_FuelSystem_IsFuelPortFlapOpen :> Boolean;
  @VssSignalMetadata about Vehicle_Powertrain_FuelSystem_IsFuelPortFlapOpen {
    path = "Vehicle.Powertrain.FuelSystem.IsFuelPortFlapOpen";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Status of the fuel port flap(s). True if at least one is open.";
    sourceComment = "";
  }

  attribute def Vehicle_Powertrain_FuelSystem_Range :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_FuelSystem_Range {
    path = "Vehicle.Powertrain.FuelSystem.Range";
    kind = "sensor";
    datatype = "uint32";
    sourceDescription = "Remaining range in meters using only liquid fuel.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_FuelSystem_Range {
    quantityReference = "ISQ::length";
    unitReference = "SI::metre";
  }

  attribute def Vehicle_Powertrain_FuelSystem_RefuelPortPosition :> Vehicle_Powertrain_FuelSystem_RefuelPortPosition_AllowedValue;
  @VssSignalMetadata about Vehicle_Powertrain_FuelSystem_RefuelPortPosition {
    path = "Vehicle.Powertrain.FuelSystem.RefuelPortPosition";
    kind = "attribute";
    datatype = "string[]";
    sourceDescription = "Position of refuel port(s). First part indicates side of vehicle, second part relative position on that side.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Powertrain_FuelSystem_RefuelPortPosition {
    allowedValues = "FRONT_LEFT, FRONT_MIDDLE, FRONT_RIGHT, REAR_LEFT, REAR_MIDDLE, REAR_RIGHT, LEFT_FRONT, LEFT_MIDDLE, LEFT_REAR, RIGHT_FRONT, RIGHT_MIDDLE, RIGHT_REAR";
  }

  attribute def Vehicle_Powertrain_FuelSystem_RelativeLevel :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_FuelSystem_RelativeLevel {
    path = "Vehicle.Powertrain.FuelSystem.RelativeLevel";
    kind = "sensor";
    datatype = "uint8";
    sourceDescription = "Level in fuel tank as percent of capacity. 0 = empty. 100 = full.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_FuelSystem_RelativeLevel {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Powertrain_FuelSystem_RelativeLevel {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Powertrain_FuelSystem_SupportedFuel :> Vehicle_Powertrain_FuelSystem_SupportedFuel_AllowedValue;
  @VssSignalMetadata about Vehicle_Powertrain_FuelSystem_SupportedFuel {
    path = "Vehicle.Powertrain.FuelSystem.SupportedFuel";
    kind = "attribute";
    datatype = "string[]";
    sourceDescription = "Detailed information on fuels supported by the vehicle. Identifiers originating from DIN EN 16942:2021-08, appendix B, with additional suffix for octane (RON) where relevant.";
    sourceComment = "RON 95 is sometimes referred to as Super, RON 98 as Super Plus.";
  }
  @VssAllowedValuesMetadata about Vehicle_Powertrain_FuelSystem_SupportedFuel {
    allowedValues = "E5_95, E5_98, E10_95, E10_98, E85, B7, B10, B20, B30, B100, XTL, LPG, CNG, LNG, H2, OTHER";
  }

  attribute def Vehicle_Powertrain_FuelSystem_SupportedFuelTypes :> Vehicle_Powertrain_FuelSystem_SupportedFuelTypes_AllowedValue;
  @VssSignalMetadata about Vehicle_Powertrain_FuelSystem_SupportedFuelTypes {
    path = "Vehicle.Powertrain.FuelSystem.SupportedFuelTypes";
    kind = "attribute";
    datatype = "string[]";
    sourceDescription = "High level information of fuel types supported";
    sourceComment = "If a vehicle also has an electric drivetrain (e.g. hybrid) that will be obvious from the PowerTrain.Type signal.";
  }
  @VssAllowedValuesMetadata about Vehicle_Powertrain_FuelSystem_SupportedFuelTypes {
    allowedValues = "GASOLINE, DIESEL, E85, LPG, CNG, LNG, H2, OTHER";
  }

  attribute def Vehicle_Powertrain_FuelSystem_TankCapacity :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_FuelSystem_TankCapacity {
    path = "Vehicle.Powertrain.FuelSystem.TankCapacity";
    kind = "attribute";
    datatype = "float";
    sourceDescription = "Capacity of the fuel tank in liters.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_FuelSystem_TankCapacity {
    quantityReference = "ISQ::volume";
    unitReference = "SI::litre";
  }

  attribute def Vehicle_Powertrain_FuelSystem_TimeRemaining :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_FuelSystem_TimeRemaining {
    path = "Vehicle.Powertrain.FuelSystem.TimeRemaining";
    kind = "sensor";
    datatype = "uint32";
    sourceDescription = "Time remaining in seconds before the fuel tank is empty.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_FuelSystem_TimeRemaining {
    quantityReference = "ISQ::time";
    unitReference = "SI::second";
  }

  attribute def Vehicle_Powertrain_IsAutoPowerOptimize :> Boolean;
  @VssSignalMetadata about Vehicle_Powertrain_IsAutoPowerOptimize {
    path = "Vehicle.Powertrain.IsAutoPowerOptimize";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Auto Power Optimization Flag When set to 'true', the system enables automatic power optimization, dynamically adjusting the power optimization level based on runtime conditions or features managed by the OEM. When set to 'false', manual control of the power optimization level is allowed.";
    sourceComment = "";
  }

  attribute def Vehicle_Powertrain_PowerOptimizeLevel :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_PowerOptimizeLevel {
    path = "Vehicle.Powertrain.PowerOptimizeLevel";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Power optimization level for this branch/subsystem. A higher number indicates more aggressive power optimization. Level 0 indicates that all functionality is enabled, no power optimization enabled. Level 10 indicates most aggressive power optimization mode, only essential functionality enabled.";
    sourceComment = "";
  }
  @VssRangeMetadata about Vehicle_Powertrain_PowerOptimizeLevel {
    minValue = "0";
    maxValue = "10";
  }

  attribute def Vehicle_Powertrain_Range :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_Range {
    path = "Vehicle.Powertrain.Range";
    kind = "sensor";
    datatype = "uint32";
    sourceDescription = "Remaining range in meters using all energy sources available in the vehicle.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_Range {
    quantityReference = "ISQ::length";
    unitReference = "SI::metre";
  }

  attribute def Vehicle_Powertrain_RangeExtender_ChargeDepleting_EnergyConsumption :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_RangeExtender_ChargeDepleting_EnergyConsumption {
    path = "Vehicle.Powertrain.RangeExtender.ChargeDepleting.EnergyConsumption";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Current electric energy consumption rate during Charge Depleting mode operation.";
    sourceComment = "This value represents the instantaneous or short-term average electric energy consumption while the vehicle is operating in CD mode. It is calculated based on the electrical energy drawn from the traction battery per distance traveled. This metric is analogous to fuel consumption but measured in electrical energy units. A lower value indicates more efficient electric operation.";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_RangeExtender_ChargeDepleting_EnergyConsumption {
    quantityReference = "ISQ::energyPerDistance";
    unitReference = "SI-derived kilowattHourPer100Kilometre";
  }

  attribute def Vehicle_Powertrain_RangeExtender_ChargeDepleting_Range :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_RangeExtender_ChargeDepleting_Range {
    path = "Vehicle.Powertrain.RangeExtender.ChargeDepleting.Range";
    kind = "sensor";
    datatype = "uint32";
    sourceDescription = "Estimated remaining distance that can be traveled in Charge Depleting mode using available battery energy.";
    sourceComment = "This range estimate is calculated based on the current battery state of charge and the recent energy consumption patterns in CD mode. The estimate may vary based on driving conditions, terrain, climate control usage, and other factors affecting battery consumption. When this range approaches zero, the vehicle will typically transition to Charge Sustaining mode.";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_RangeExtender_ChargeDepleting_Range {
    quantityReference = "ISQ::length";
    unitReference = "SI::metre";
  }

  attribute def Vehicle_Powertrain_RangeExtender_ChargeSustaining_FuelEconomy :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_RangeExtender_ChargeSustaining_FuelEconomy {
    path = "Vehicle.Powertrain.RangeExtender.ChargeSustaining.FuelEconomy";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Current fuel economy during Charge Sustaining mode operation.";
    sourceComment = "This value represents the fuel efficiency when the engine is operating as a generator to maintain battery charge. It differs from conventional vehicle fuel economy because the engine is optimized to run at efficient generator speeds rather than varying speeds for direct wheel propulsion. The actual fuel economy in CS mode may be different from the vehicle's rated CS mode fuel economy depending on driving conditions and power demands.";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_RangeExtender_ChargeSustaining_FuelEconomy {
    quantityReference = "ISQ::fuelEfficiency";
    unitReference = "SI-derived kilometre/litre";
  }

  attribute def Vehicle_Powertrain_RangeExtender_ChargeSustaining_Range :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_RangeExtender_ChargeSustaining_Range {
    path = "Vehicle.Powertrain.RangeExtender.ChargeSustaining.Range";
    kind = "sensor";
    datatype = "uint32";
    sourceDescription = "Estimated remaining distance that can be traveled in Charge Sustaining mode using available fuel.";
    sourceComment = "This range estimate is calculated based on the current fuel level and recent fuel consumption patterns in CS mode. It represents the extended range capability provided by the internal combustion engine. The total vehicle range is the sum of CD mode range and CS mode range.";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_RangeExtender_ChargeSustaining_Range {
    quantityReference = "ISQ::length";
    unitReference = "SI::metre";
  }

  attribute def Vehicle_Powertrain_RangeExtender_CombinedFuelEconomy :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_RangeExtender_CombinedFuelEconomy {
    path = "Vehicle.Powertrain.RangeExtender.CombinedFuelEconomy";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Combined fuel economy equivalent that accounts for both electric energy and fuel consumption.";
    sourceComment = "This metric provides a unified measure of overall vehicle efficiency by converting electric energy consumption to a fuel-equivalent value and combining it with actual fuel consumption. The calculation typically follows regulatory standards (such as EPA MPGe) that define the equivalence between electrical energy and liquid fuel energy. For example, EPA defines 33.7 kWh as equivalent to one gallon of gasoline. This combined metric is useful for comparing EREV efficiency with conventional vehicles and understanding the overall energy cost of operation. The value is weighted based on the proportion of driving in CD versus CS modes.";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_RangeExtender_CombinedFuelEconomy {
    quantityReference = "ISQ::fuelEfficiency";
    unitReference = "SI-derived kilometre/litre";
  }

  attribute def Vehicle_Powertrain_RangeExtender_OperatingMode :> Vehicle_Powertrain_RangeExtender_OperatingMode_AllowedValue;
  @VssSignalMetadata about Vehicle_Powertrain_RangeExtender_OperatingMode {
    path = "Vehicle.Powertrain.RangeExtender.OperatingMode";
    kind = "sensor";
    datatype = "string";
    sourceDescription = "Current operating mode of the Extended Range Electric Vehicle.";
    sourceComment = "CHARGE_DEPLETING (CD) - Vehicle operates primarily on battery power, battery SOC decreases. CHARGE_SUSTAINING (CS) - Engine operates as generator to maintain battery charge level. BLENDED - Both battery and engine are used simultaneously, typically during high power demands. The mode transition typically occurs automatically based on battery state of charge thresholds.";
  }
  @VssAllowedValuesMetadata about Vehicle_Powertrain_RangeExtender_OperatingMode {
    allowedValues = "CHARGE_DEPLETING, CHARGE_SUSTAINING, BLENDED";
  }

  attribute def Vehicle_Powertrain_TimeRemaining :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_TimeRemaining {
    path = "Vehicle.Powertrain.TimeRemaining";
    kind = "sensor";
    datatype = "uint32";
    sourceDescription = "Time remaining in seconds before all energy sources available in the vehicle are empty.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TimeRemaining {
    quantityReference = "ISQ::time";
    unitReference = "SI::second";
  }

  attribute def Vehicle_Powertrain_TractionBattery_AccumulatedChargedEnergy :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_AccumulatedChargedEnergy {
    path = "Vehicle.Powertrain.TractionBattery.AccumulatedChargedEnergy";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "The accumulated energy delivered to the battery during charging over lifetime of the battery.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_AccumulatedChargedEnergy {
    quantityReference = "ISQ::energy";
    unitReference = "SI::kilowattHour";
  }

  attribute def Vehicle_Powertrain_TractionBattery_AccumulatedChargedThroughput :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_AccumulatedChargedThroughput {
    path = "Vehicle.Powertrain.TractionBattery.AccumulatedChargedThroughput";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "The accumulated charge throughput delivered to the battery during charging over lifetime of the battery.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_AccumulatedChargedThroughput {
    quantityReference = "ISQ::electricCharge";
    unitReference = "SI::ampereHour";
  }

  attribute def Vehicle_Powertrain_TractionBattery_AccumulatedConsumedEnergy :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_AccumulatedConsumedEnergy {
    path = "Vehicle.Powertrain.TractionBattery.AccumulatedConsumedEnergy";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "The accumulated energy leaving HV battery for propulsion and auxiliary loads over lifetime of the battery.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_AccumulatedConsumedEnergy {
    quantityReference = "ISQ::energy";
    unitReference = "SI::kilowattHour";
  }

  attribute def Vehicle_Powertrain_TractionBattery_AccumulatedConsumedThroughput :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_AccumulatedConsumedThroughput {
    path = "Vehicle.Powertrain.TractionBattery.AccumulatedConsumedThroughput";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "The accumulated charge throughput leaving HV battery for propulsion and auxiliary loads over lifetime of the battery.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_AccumulatedConsumedThroughput {
    quantityReference = "ISQ::electricCharge";
    unitReference = "SI::ampereHour";
  }

  attribute def Vehicle_Powertrain_TractionBattery_BatteryConditioning_IsActive :> Boolean;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_BatteryConditioning_IsActive {
    path = "Vehicle.Powertrain.TractionBattery.BatteryConditioning.IsActive";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if battery conditioning is active (i.e. actively monitors battery temperature). True = Active. False = Inactive.";
    sourceComment = "This signal is typically true when mode is not INACTIVE and time is within defined start/end times.";
  }

  attribute def Vehicle_Powertrain_TractionBattery_BatteryConditioning_IsOngoing :> Boolean;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_BatteryConditioning_IsOngoing {
    path = "Vehicle.Powertrain.TractionBattery.BatteryConditioning.IsOngoing";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicating if battery conditioning is currently ongoing. Battery conditioning is considered ongoing when the battery conditioning system is actively heating or cooling the battery, or requesting heating or cooling.";
    sourceComment = "When battery conditioning is active, but temperature is already within acceptable range so that no cooling or heating is needed then IsOngoing shall report False.";
  }

  attribute def Vehicle_Powertrain_TractionBattery_BatteryConditioning_RequestedMode :> Vehicle_Powertrain_TractionBattery_BatteryConditioning_RequestedMode_AllowedValue;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_BatteryConditioning_RequestedMode {
    path = "Vehicle.Powertrain.TractionBattery.BatteryConditioning.RequestedMode";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Defines requested mode for battery conditioning. INACTIVE - Battery conditioning inactive. FAST_CHARGING_PREPARATION - Battery conditioning for fast charging. DRIVING_PREPARATION - Battery conditioning for driving.";
    sourceComment = "The Mode and TargetTime can be used to calculate TargetTemperature and StartTime";
  }
  @VssAllowedValuesMetadata about Vehicle_Powertrain_TractionBattery_BatteryConditioning_RequestedMode {
    allowedValues = "INACTIVE, FAST_CHARGING_PREPARATION, DRIVING_PREPARATION";
  }

  attribute def Vehicle_Powertrain_TractionBattery_BatteryConditioning_StartTime :> String;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_BatteryConditioning_StartTime {
    path = "Vehicle.Powertrain.TractionBattery.BatteryConditioning.StartTime";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Start time for battery conditioning, formatted according to ISO 8601 with UTC time zone.";
    sourceComment = "If the vehicle is asleep, this is the time the vehicle and the battery conditioning system must wake up and start monitoring the battery and if necessary start heating/cooling of the battery.";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_BatteryConditioning_StartTime {
    quantityReference = "n/a";
    unitReference = "ISO 8601 lexical date/time string";
  }

  attribute def Vehicle_Powertrain_TractionBattery_BatteryConditioning_TargetTemperature :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_BatteryConditioning_TargetTemperature {
    path = "Vehicle.Powertrain.TractionBattery.BatteryConditioning.TargetTemperature";
    kind = "actuator";
    datatype = "float";
    sourceDescription = "Target temperature for battery conditioning.";
    sourceComment = "Target temperature possibly differs between different modes as well as other factors. Allowed deviation from target temperature is implementation dependent.";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_BatteryConditioning_TargetTemperature {
    quantityReference = "ISQ::thermodynamicTemperature";
    unitReference = "SI::degreeCelsius";
  }

  attribute def Vehicle_Powertrain_TractionBattery_BatteryConditioning_TargetTime :> String;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_BatteryConditioning_TargetTime {
    path = "Vehicle.Powertrain.TractionBattery.BatteryConditioning.TargetTime";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Target time when conditioning shall be finished, formatted according to ISO 8601 with UTC time zone.";
    sourceComment = "For FAST_CHARGING mode this is typically the time when charging is supposed to start. For DRIVING mode this is typically the expected departure time. Battery conditioning will be deactivated when this time has passed.";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_BatteryConditioning_TargetTime {
    quantityReference = "n/a";
    unitReference = "ISO 8601 lexical date/time string";
  }

  attribute def Vehicle_Powertrain_TractionBattery_CellVoltage_CellVoltages :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_CellVoltage_CellVoltages {
    path = "Vehicle.Powertrain.TractionBattery.CellVoltage.CellVoltages";
    kind = "sensor";
    datatype = "float[]";
    sourceDescription = "Array of cell voltages. Length or array shall correspond to number of cells in vehicle.";
    sourceComment = "Cells are identified by relative position in array.";
  }

  attribute def Vehicle_Powertrain_TractionBattery_CellVoltage_IdMax :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_CellVoltage_IdMax {
    path = "Vehicle.Powertrain.TractionBattery.CellVoltage.IdMax";
    kind = "sensor";
    datatype = "uint16";
    sourceDescription = "Identifier of the battery cell with highest voltage.";
    sourceComment = "Identifier is supposed to be relative index of the cell, starting with 0 the first cell.";
  }

  attribute def Vehicle_Powertrain_TractionBattery_CellVoltage_IdMin :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_CellVoltage_IdMin {
    path = "Vehicle.Powertrain.TractionBattery.CellVoltage.IdMin";
    kind = "sensor";
    datatype = "uint16";
    sourceDescription = "Identifier of the battery cell with lowest voltage.";
    sourceComment = "Identifier is supposed to be relative index of the cell, starting with 0 the first cell.";
  }

  attribute def Vehicle_Powertrain_TractionBattery_CellVoltage_Max :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_CellVoltage_Max {
    path = "Vehicle.Powertrain.TractionBattery.CellVoltage.Max";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Current voltage of the battery cell with highest voltage.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_CellVoltage_Max {
    quantityReference = "ISQ::electricPotential";
    unitReference = "SI::volt";
  }

  attribute def Vehicle_Powertrain_TractionBattery_CellVoltage_Min :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_CellVoltage_Min {
    path = "Vehicle.Powertrain.TractionBattery.CellVoltage.Min";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Current voltage of the battery cell with lowest voltage.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_CellVoltage_Min {
    quantityReference = "ISQ::electricPotential";
    unitReference = "SI::volt";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_AveragePower :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_AveragePower {
    path = "Vehicle.Powertrain.TractionBattery.Charging.AveragePower";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Average charging power of last or current charging event.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Charging_AveragePower {
    quantityReference = "ISQ::power";
    unitReference = "SI::kilowatt";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargeCurrent_DC :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_ChargeCurrent_DC {
    path = "Vehicle.Powertrain.TractionBattery.Charging.ChargeCurrent.DC";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Current DC charging current at inlet. Negative if returning energy to grid.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Charging_ChargeCurrent_DC {
    quantityReference = "ISQ::electricCurrent";
    unitReference = "SI::ampere";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargeCurrent_Phase1 :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_ChargeCurrent_Phase1 {
    path = "Vehicle.Powertrain.TractionBattery.Charging.ChargeCurrent.Phase1";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Current AC charging current (rms) at inlet for Phase 1. Negative if returning energy to grid.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Charging_ChargeCurrent_Phase1 {
    quantityReference = "ISQ::electricCurrent";
    unitReference = "SI::ampere";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargeCurrent_Phase2 :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_ChargeCurrent_Phase2 {
    path = "Vehicle.Powertrain.TractionBattery.Charging.ChargeCurrent.Phase2";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Current AC charging current (rms) at inlet for Phase 2. Negative if returning energy to grid.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Charging_ChargeCurrent_Phase2 {
    quantityReference = "ISQ::electricCurrent";
    unitReference = "SI::ampere";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargeCurrent_Phase3 :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_ChargeCurrent_Phase3 {
    path = "Vehicle.Powertrain.TractionBattery.Charging.ChargeCurrent.Phase3";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Current AC charging current (rms) at inlet for Phase 3. Negative if returning energy to grid.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Charging_ChargeCurrent_Phase3 {
    quantityReference = "ISQ::electricCurrent";
    unitReference = "SI::ampere";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargeLimit :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_ChargeLimit {
    path = "Vehicle.Powertrain.TractionBattery.Charging.ChargeLimit";
    kind = "actuator";
    datatype = "uint8";
    sourceDescription = "Target charge limit (state of charge) for battery.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Charging_ChargeLimit {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Powertrain_TractionBattery_Charging_ChargeLimit {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargeRate :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_ChargeRate {
    path = "Vehicle.Powertrain.TractionBattery.Charging.ChargeRate";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Current charging rate, as in kilometers of range added per hour.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Charging_ChargeRate {
    quantityReference = "ISQ::speed";
    unitReference = "SI::kilometrePerHour";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargeVoltage_DC :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_ChargeVoltage_DC {
    path = "Vehicle.Powertrain.TractionBattery.Charging.ChargeVoltage.DC";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Current DC charging voltage at charging inlet.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Charging_ChargeVoltage_DC {
    quantityReference = "ISQ::electricPotential";
    unitReference = "SI::volt";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargeVoltage_Phase1 :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_ChargeVoltage_Phase1 {
    path = "Vehicle.Powertrain.TractionBattery.Charging.ChargeVoltage.Phase1";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Current AC charging voltage (rms) at inlet for Phase 1.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Charging_ChargeVoltage_Phase1 {
    quantityReference = "ISQ::electricPotential";
    unitReference = "SI::volt";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargeVoltage_Phase2 :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_ChargeVoltage_Phase2 {
    path = "Vehicle.Powertrain.TractionBattery.Charging.ChargeVoltage.Phase2";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Current AC charging voltage (rms) at inlet for Phase 2.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Charging_ChargeVoltage_Phase2 {
    quantityReference = "ISQ::electricPotential";
    unitReference = "SI::volt";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargeVoltage_Phase3 :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_ChargeVoltage_Phase3 {
    path = "Vehicle.Powertrain.TractionBattery.Charging.ChargeVoltage.Phase3";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Current AC charging voltage (rms) at inlet for Phase 3.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Charging_ChargeVoltage_Phase3 {
    quantityReference = "ISQ::electricPotential";
    unitReference = "SI::volt";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargingPort_IsChargingCableConnected :> Boolean;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_ChargingPort_IsChargingCableConnected {
    path = "Vehicle.Powertrain.TractionBattery.Charging.ChargingPort.IsChargingCableConnected";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates whether a charging cable is physically connected to a particular charging port or not.";
    sourceComment = "";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargingPort_IsChargingCableLocked :> Boolean;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_ChargingPort_IsChargingCableLocked {
    path = "Vehicle.Powertrain.TractionBattery.Charging.ChargingPort.IsChargingCableLocked";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is charging cable locked to prevent removal.";
    sourceComment = "Locking of charging cable can be used to prevent unintentional removing during charging.";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargingPort_IsFlapOpen :> Boolean;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_ChargingPort_IsFlapOpen {
    path = "Vehicle.Powertrain.TractionBattery.Charging.ChargingPort.IsFlapOpen";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Status of the charging port flap(s).";
    sourceComment = "True = at least one flap of this port is open, False = All flaps of this port are closed.";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_ChargingPort_SupportedInletTypes :> Vehicle_Powertrain_TractionBattery_Charging_ChargingPort_SupportedInletTypes_AllowedValue;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_ChargingPort_SupportedInletTypes {
    path = "Vehicle.Powertrain.TractionBattery.Charging.ChargingPort.SupportedInletTypes";
    kind = "attribute";
    datatype = "string[]";
    sourceDescription = "A list of the supported (i.e., available) charging inlets in a particular charging port. IEC types refer to IEC 62196, GBT refers to GB/T 20234.";
    sourceComment = "A vehicle may have multiple charging ports. IEC_TYPE_1_AC refers to Type 1 as defined in IEC 62196-2. Also known as Yazaki or J1772 connector. IEC_TYPE_2_AC refers to Type 2 as defined in IEC 62196-2. Also known as Mennekes connector. IEC_TYPE_3_AC refers to Type 3 as defined in IEC 62196-2. Also known as Scame connector. IEC_TYPE_4_DC refers to AA configuration as defined in IEC 62196-3. Also known as Type 4 or CHAdeMO connector. IEC_TYPE_1_CCS_DC refers to EE Configuration as defined in IEC 62196-3. Also known as CCS1 or Combo1 connector. IEC_TYPE_2_CCS_DC refers to FF Configuration as defined in IEC 62196-3. Also known as CCS2 or Combo2 connector. TESLA_ROADSTER, TESLA_HPWC (High Power Wall Connector) and TESLA_SUPERCHARGER refer to non-standardized charging ports/methods used by Tesla. GBT_AC refers to connector specified in GB/T 20234.2. GBT_DC refers to connector specified in GB/T 20234.3. Also specified as BB Configuration in IEC 62196-3. OTHER shall be used for charging ports not included in the list above. For additional information see https://en.wikipedia.org/wiki/IEC_62196.";
  }
  @VssAllowedValuesMetadata about Vehicle_Powertrain_TractionBattery_Charging_ChargingPort_SupportedInletTypes {
    allowedValues = "IEC_TYPE_1_AC, IEC_TYPE_2_AC, IEC_TYPE_3_AC, IEC_TYPE_4_DC, IEC_TYPE_1_CCS_DC, IEC_TYPE_2_CCS_DC, TESLA_ROADSTER, TESLA_HPWC, TESLA_SUPERCHARGER, GBT_AC, GBT_DC, OTHER";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_EvseId :> String;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_EvseId {
    path = "Vehicle.Powertrain.TractionBattery.Charging.EvseId";
    kind = "sensor";
    datatype = "string";
    sourceDescription = "EVSE charging point ID (without separators) of last or current charging event according to ISO 15118-2 Annex H.";
    sourceComment = "Length of id between 7 and 37 characters. ZZ00000 to be used if SECC cannot provide id";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_IsCharging :> Boolean;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_IsCharging {
    path = "Vehicle.Powertrain.TractionBattery.Charging.IsCharging";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "True if charging is ongoing. Charging is considered to be ongoing if energy is flowing from charger to vehicle.";
    sourceComment = "";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_IsDischarging :> Boolean;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_IsDischarging {
    path = "Vehicle.Powertrain.TractionBattery.Charging.IsDischarging";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "True if discharging (vehicle to grid) is ongoing. Discharging is considered to be ongoing if energy is flowing from vehicle to charger/grid.";
    sourceComment = "";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_Location_Altitude :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_Location_Altitude {
    path = "Vehicle.Powertrain.TractionBattery.Charging.Location.Altitude";
    kind = "sensor";
    datatype = "double";
    sourceDescription = "Altitude relative to WGS 84 reference ellipsoid of last or current charging event.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Charging_Location_Altitude {
    quantityReference = "ISQ::length";
    unitReference = "SI::metre";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_Location_Latitude :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_Location_Latitude {
    path = "Vehicle.Powertrain.TractionBattery.Charging.Location.Latitude";
    kind = "sensor";
    datatype = "double";
    sourceDescription = "Latitude of last or current charging event in WGS 84 geodetic coordinates.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Charging_Location_Latitude {
    quantityReference = "ISQ::planeAngle";
    unitReference = "SI::degree";
  }
  @VssRangeMetadata about Vehicle_Powertrain_TractionBattery_Charging_Location_Latitude {
    minValue = "-90";
    maxValue = "90";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_Location_Longitude :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_Location_Longitude {
    path = "Vehicle.Powertrain.TractionBattery.Charging.Location.Longitude";
    kind = "sensor";
    datatype = "double";
    sourceDescription = "Longitude of last or current charging event in WGS 84 geodetic coordinates.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Charging_Location_Longitude {
    quantityReference = "ISQ::planeAngle";
    unitReference = "SI::degree";
  }
  @VssRangeMetadata about Vehicle_Powertrain_TractionBattery_Charging_Location_Longitude {
    minValue = "-180";
    maxValue = "180";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_MaxPower :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_MaxPower {
    path = "Vehicle.Powertrain.TractionBattery.Charging.MaxPower";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Maximum charging power of last or current charging event.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Charging_MaxPower {
    quantityReference = "ISQ::power";
    unitReference = "SI::kilowatt";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_MaximumChargingCurrent_DC :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_MaximumChargingCurrent_DC {
    path = "Vehicle.Powertrain.TractionBattery.Charging.MaximumChargingCurrent.DC";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Maximum DC charging current at inlet that can be accepted by the system.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Charging_MaximumChargingCurrent_DC {
    quantityReference = "ISQ::electricCurrent";
    unitReference = "SI::ampere";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_MaximumChargingCurrent_Phase1 :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_MaximumChargingCurrent_Phase1 {
    path = "Vehicle.Powertrain.TractionBattery.Charging.MaximumChargingCurrent.Phase1";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Maximum AC charging current (rms) at inlet for Phase 1 that can be accepted by the system.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Charging_MaximumChargingCurrent_Phase1 {
    quantityReference = "ISQ::electricCurrent";
    unitReference = "SI::ampere";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_MaximumChargingCurrent_Phase2 :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_MaximumChargingCurrent_Phase2 {
    path = "Vehicle.Powertrain.TractionBattery.Charging.MaximumChargingCurrent.Phase2";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Maximum AC charging current (rms) at inlet for Phase 2 that can be accepted by the system.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Charging_MaximumChargingCurrent_Phase2 {
    quantityReference = "ISQ::electricCurrent";
    unitReference = "SI::ampere";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_MaximumChargingCurrent_Phase3 :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_MaximumChargingCurrent_Phase3 {
    path = "Vehicle.Powertrain.TractionBattery.Charging.MaximumChargingCurrent.Phase3";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Maximum AC charging current (rms) at inlet for Phase 3 that can be accepted by the system.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Charging_MaximumChargingCurrent_Phase3 {
    quantityReference = "ISQ::electricCurrent";
    unitReference = "SI::ampere";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_PowerLoss :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_PowerLoss {
    path = "Vehicle.Powertrain.TractionBattery.Charging.PowerLoss";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Electrical energy lost by power dissipation to heat inside the AC/DC converter.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Charging_PowerLoss {
    quantityReference = "ISQ::power";
    unitReference = "SI::watt";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_StartStopCharging :> Vehicle_Powertrain_TractionBattery_Charging_StartStopCharging_AllowedValue;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_StartStopCharging {
    path = "Vehicle.Powertrain.TractionBattery.Charging.StartStopCharging";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Start or stop the charging process.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Powertrain_TractionBattery_Charging_StartStopCharging {
    allowedValues = "START, STOP";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_Temperature :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_Temperature {
    path = "Vehicle.Powertrain.TractionBattery.Charging.Temperature";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Current temperature of AC/DC converter converting grid voltage to battery voltage.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Charging_Temperature {
    quantityReference = "ISQ::thermodynamicTemperature";
    unitReference = "SI::degreeCelsius";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_TimeToComplete :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_TimeToComplete {
    path = "Vehicle.Powertrain.TractionBattery.Charging.TimeToComplete";
    kind = "sensor";
    datatype = "uint32";
    sourceDescription = "The time needed for the current charging process to reach Charging.ChargeLimit. 0 if charging is complete or no charging process is active or planned.";
    sourceComment = "Shall consider time set by Charging.Timer.Time. E.g. if charging shall start in 3 hours and 2 hours of charging is needed, then Charging.TimeToComplete shall report 5 hours.";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Charging_TimeToComplete {
    quantityReference = "ISQ::time";
    unitReference = "SI::second";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_Timer_Mode :> Vehicle_Powertrain_TractionBattery_Charging_Timer_Mode_AllowedValue;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_Timer_Mode {
    path = "Vehicle.Powertrain.TractionBattery.Charging.Timer.Mode";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Defines timer mode for charging: INACTIVE - no timer set, charging may start as soon as battery is connected to a charger. START_TIME - charging shall start at Charging.Timer.Time. END_TIME - charging shall be finished (reach Charging.ChargeLimit) at Charging.Timer.Time. When charging is completed the vehicle shall change mode to 'inactive' or set a new Charging.Timer.Time. Charging shall start immediately if mode is 'starttime' or 'endtime' and Charging.Timer.Time is a time in the past.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Powertrain_TractionBattery_Charging_Timer_Mode {
    allowedValues = "INACTIVE, START_TIME, END_TIME";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Charging_Timer_Time :> String;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Charging_Timer_Time {
    path = "Vehicle.Powertrain.TractionBattery.Charging.Timer.Time";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Time for next charging-related action, formatted according to ISO 8601 with UTC time zone. Value has no significance if Charging.Timer.Mode is 'inactive'.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Charging_Timer_Time {
    quantityReference = "n/a";
    unitReference = "ISO 8601 lexical date/time string";
  }

  attribute def Vehicle_Powertrain_TractionBattery_CurrentCurrent :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_CurrentCurrent {
    path = "Vehicle.Powertrain.TractionBattery.CurrentCurrent";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Current current flowing in/out of battery. Positive = Current flowing in to battery, e.g. during charging. Negative = Current flowing out of battery, e.g. during driving.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_CurrentCurrent {
    quantityReference = "ISQ::electricCurrent";
    unitReference = "SI::ampere";
  }

  attribute def Vehicle_Powertrain_TractionBattery_CurrentPower :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_CurrentPower {
    path = "Vehicle.Powertrain.TractionBattery.CurrentPower";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Current electrical energy flowing in/out of battery. Positive = Energy flowing in to battery, e.g. during charging. Negative = Energy flowing out of battery, e.g. during driving.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_CurrentPower {
    quantityReference = "ISQ::power";
    unitReference = "SI::watt";
  }

  attribute def Vehicle_Powertrain_TractionBattery_CurrentVoltage :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_CurrentVoltage {
    path = "Vehicle.Powertrain.TractionBattery.CurrentVoltage";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Current Voltage of the battery.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_CurrentVoltage {
    quantityReference = "ISQ::electricPotential";
    unitReference = "SI::volt";
  }

  attribute def Vehicle_Powertrain_TractionBattery_DCDC_PowerLoss :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_DCDC_PowerLoss {
    path = "Vehicle.Powertrain.TractionBattery.DCDC.PowerLoss";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Electrical energy lost by power dissipation to heat inside DC/DC converter.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_DCDC_PowerLoss {
    quantityReference = "ISQ::power";
    unitReference = "SI::watt";
  }

  attribute def Vehicle_Powertrain_TractionBattery_DCDC_Temperature :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_DCDC_Temperature {
    path = "Vehicle.Powertrain.TractionBattery.DCDC.Temperature";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Current temperature of DC/DC converter converting battery high voltage to vehicle low voltage (typically 12 Volts).";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_DCDC_Temperature {
    quantityReference = "ISQ::thermodynamicTemperature";
    unitReference = "SI::degreeCelsius";
  }

  attribute def Vehicle_Powertrain_TractionBattery_ErrorCodes :> String;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_ErrorCodes {
    path = "Vehicle.Powertrain.TractionBattery.ErrorCodes";
    kind = "sensor";
    datatype = "string[]";
    sourceDescription = "Current error codes related to the battery, if any.";
    sourceComment = "Error code format is not defined, it may be DTCs according to OBD II (SAE-J2012DA_201812) standard ([P|C|B|U]XXXXX ) or any other format.";
  }

  attribute def Vehicle_Powertrain_TractionBattery_GrossCapacity :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_GrossCapacity {
    path = "Vehicle.Powertrain.TractionBattery.GrossCapacity";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Gross capacity of the battery.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_GrossCapacity {
    quantityReference = "ISQ::energy";
    unitReference = "SI::kilowattHour";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Id :> String;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Id {
    path = "Vehicle.Powertrain.TractionBattery.Id";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "Battery Identification Number as assigned by OEM.";
    sourceComment = "This could be serial number, part number plus serial number, UUID, or any other identifier that the OEM want to use to uniquely identify the battery individual.";
  }

  attribute def Vehicle_Powertrain_TractionBattery_IsGroundConnected :> Boolean;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_IsGroundConnected {
    path = "Vehicle.Powertrain.TractionBattery.IsGroundConnected";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicating if the ground (negative terminator) of the traction battery is connected to the powertrain.";
    sourceComment = "It might be possible to disconnect the traction battery used by an electric powertrain. This is achieved by connectors, typically one for plus and one for minus.";
  }

  attribute def Vehicle_Powertrain_TractionBattery_IsPowerConnected :> Boolean;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_IsPowerConnected {
    path = "Vehicle.Powertrain.TractionBattery.IsPowerConnected";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicating if the power (positive terminator) of the traction battery is connected to the powertrain.";
    sourceComment = "It might be possible to disconnect the traction battery used by an electric powertrain. This is achieved by connectors, typically one for plus and one for minus.";
  }

  attribute def Vehicle_Powertrain_TractionBattery_MaxVoltage :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_MaxVoltage {
    path = "Vehicle.Powertrain.TractionBattery.MaxVoltage";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Max allowed voltage of the battery, e.g. during charging.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_MaxVoltage {
    quantityReference = "ISQ::electricPotential";
    unitReference = "SI::volt";
  }

  attribute def Vehicle_Powertrain_TractionBattery_NetCapacity :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_NetCapacity {
    path = "Vehicle.Powertrain.TractionBattery.NetCapacity";
    kind = "sensor";
    datatype = "uint16";
    sourceDescription = "Total net capacity of the battery considering aging.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_NetCapacity {
    quantityReference = "ISQ::energy";
    unitReference = "SI::kilowattHour";
  }

  attribute def Vehicle_Powertrain_TractionBattery_NominalVoltage :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_NominalVoltage {
    path = "Vehicle.Powertrain.TractionBattery.NominalVoltage";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Nominal Voltage of the battery.";
    sourceComment = "Nominal voltage typically refers to voltage of fully charged battery when delivering rated capacity.";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_NominalVoltage {
    quantityReference = "ISQ::electricPotential";
    unitReference = "SI::volt";
  }

  attribute def Vehicle_Powertrain_TractionBattery_PowerLoss :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_PowerLoss {
    path = "Vehicle.Powertrain.TractionBattery.PowerLoss";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Electrical energy lost by power dissipation to heat inside the battery.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_PowerLoss {
    quantityReference = "ISQ::power";
    unitReference = "SI::watt";
  }

  attribute def Vehicle_Powertrain_TractionBattery_ProductionDate :> String;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_ProductionDate {
    path = "Vehicle.Powertrain.TractionBattery.ProductionDate";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "Production date of battery in ISO8601 format, e.g. YYYY-MM-DD.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_ProductionDate {
    quantityReference = "n/a";
    unitReference = "ISO 8601 lexical date/time string";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Range :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Range {
    path = "Vehicle.Powertrain.TractionBattery.Range";
    kind = "sensor";
    datatype = "uint32";
    sourceDescription = "Remaining range in meters using only battery.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Range {
    quantityReference = "ISQ::length";
    unitReference = "SI::metre";
  }

  attribute def Vehicle_Powertrain_TractionBattery_StateOfCharge_Current :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_StateOfCharge_Current {
    path = "Vehicle.Powertrain.TractionBattery.StateOfCharge.Current";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Physical state of charge of the high voltage battery, relative to net capacity. This is not necessarily the state of charge being displayed to the customer.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_StateOfCharge_Current {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Powertrain_TractionBattery_StateOfCharge_Current {
    minValue = "0";
    maxValue = "100.0";
  }

  attribute def Vehicle_Powertrain_TractionBattery_StateOfCharge_CurrentEnergy :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_StateOfCharge_CurrentEnergy {
    path = "Vehicle.Powertrain.TractionBattery.StateOfCharge.CurrentEnergy";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Physical state of charge of high voltage battery expressed in kWh.";
    sourceComment = "Current energy could be calculated as .StateOfCharge.Current * .NetCapacity.";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_StateOfCharge_CurrentEnergy {
    quantityReference = "ISQ::energy";
    unitReference = "SI::kilowattHour";
  }

  attribute def Vehicle_Powertrain_TractionBattery_StateOfCharge_Displayed :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_StateOfCharge_Displayed {
    path = "Vehicle.Powertrain.TractionBattery.StateOfCharge.Displayed";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "State of charge displayed to the customer.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_StateOfCharge_Displayed {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Powertrain_TractionBattery_StateOfCharge_Displayed {
    minValue = "0";
    maxValue = "100.0";
  }

  attribute def Vehicle_Powertrain_TractionBattery_StateOfHealth :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_StateOfHealth {
    path = "Vehicle.Powertrain.TractionBattery.StateOfHealth";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Calculated battery state of health at standard conditions.";
    sourceComment = "Exact formula is implementation dependent. Could be e.g. current capacity at 20 degrees Celsius divided with original capacity at the same temperature.";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_StateOfHealth {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Powertrain_TractionBattery_StateOfHealth {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Temperature_Average :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Temperature_Average {
    path = "Vehicle.Powertrain.TractionBattery.Temperature.Average";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Current average temperature of the battery cells.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Temperature_Average {
    quantityReference = "ISQ::thermodynamicTemperature";
    unitReference = "SI::degreeCelsius";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Temperature_CellTemperature :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Temperature_CellTemperature {
    path = "Vehicle.Powertrain.TractionBattery.Temperature.CellTemperature";
    kind = "sensor";
    datatype = "float[]";
    sourceDescription = "Array of cell temperatures. Length or array shall correspond to number of cells in vehicle.";
    sourceComment = "Cells are identified by relative position in array.";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Temperature_Max :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Temperature_Max {
    path = "Vehicle.Powertrain.TractionBattery.Temperature.Max";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Current maximum temperature of the battery cells, i.e. temperature of the hottest cell.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Temperature_Max {
    quantityReference = "ISQ::thermodynamicTemperature";
    unitReference = "SI::degreeCelsius";
  }

  attribute def Vehicle_Powertrain_TractionBattery_Temperature_Min :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_Temperature_Min {
    path = "Vehicle.Powertrain.TractionBattery.Temperature.Min";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Current minimum temperature of the battery cells, i.e. temperature of the coldest cell.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_Temperature_Min {
    quantityReference = "ISQ::thermodynamicTemperature";
    unitReference = "SI::degreeCelsius";
  }

  attribute def Vehicle_Powertrain_TractionBattery_TimeRemaining :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_TractionBattery_TimeRemaining {
    path = "Vehicle.Powertrain.TractionBattery.TimeRemaining";
    kind = "sensor";
    datatype = "uint32";
    sourceDescription = "Time remaining in seconds before the battery is empty.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_TractionBattery_TimeRemaining {
    quantityReference = "ISQ::time";
    unitReference = "SI::second";
  }

  attribute def Vehicle_Powertrain_Transmission_ClutchEngagement :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_Transmission_ClutchEngagement {
    path = "Vehicle.Powertrain.Transmission.ClutchEngagement";
    kind = "actuator";
    datatype = "float";
    sourceDescription = "Clutch engagement. 0% = Clutch fully disengaged. 100% = Clutch fully engaged.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_Transmission_ClutchEngagement {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Powertrain_Transmission_ClutchEngagement {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Powertrain_Transmission_ClutchWear :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_Transmission_ClutchWear {
    path = "Vehicle.Powertrain.Transmission.ClutchWear";
    kind = "sensor";
    datatype = "uint8";
    sourceDescription = "Clutch wear as a percent. 0 = no wear. 100 = worn.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_Transmission_ClutchWear {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Powertrain_Transmission_ClutchWear {
    minValue = "";
    maxValue = "100";
  }

  attribute def Vehicle_Powertrain_Transmission_CurrentGear :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_Transmission_CurrentGear {
    path = "Vehicle.Powertrain.Transmission.CurrentGear";
    kind = "sensor";
    datatype = "int8";
    sourceDescription = "The current gear. 0=Neutral, 1/2/..=Forward, -1/-2/..=Reverse.";
    sourceComment = "";
  }

  attribute def Vehicle_Powertrain_Transmission_DiffLockFrontEngagement :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_Transmission_DiffLockFrontEngagement {
    path = "Vehicle.Powertrain.Transmission.DiffLockFrontEngagement";
    kind = "actuator";
    datatype = "float";
    sourceDescription = "Front Diff Lock engagement. 0% = Diff lock fully disengaged. 100% = Diff lock fully engaged.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_Transmission_DiffLockFrontEngagement {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Powertrain_Transmission_DiffLockFrontEngagement {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Powertrain_Transmission_DiffLockRearEngagement :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_Transmission_DiffLockRearEngagement {
    path = "Vehicle.Powertrain.Transmission.DiffLockRearEngagement";
    kind = "actuator";
    datatype = "float";
    sourceDescription = "Rear Diff Lock engagement. 0% = Diff lock fully disengaged. 100% = Diff lock fully engaged.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_Transmission_DiffLockRearEngagement {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Powertrain_Transmission_DiffLockRearEngagement {
    minValue = "0";
    maxValue = "100";
  }

  attribute def Vehicle_Powertrain_Transmission_DriveType :> Vehicle_Powertrain_Transmission_DriveType_AllowedValue;
  @VssSignalMetadata about Vehicle_Powertrain_Transmission_DriveType {
    path = "Vehicle.Powertrain.Transmission.DriveType";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "Drive type.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Powertrain_Transmission_DriveType {
    allowedValues = "UNKNOWN, FORWARD_WHEEL_DRIVE, REAR_WHEEL_DRIVE, ALL_WHEEL_DRIVE";
  }

  attribute def Vehicle_Powertrain_Transmission_GearChangeMode :> Vehicle_Powertrain_Transmission_GearChangeMode_AllowedValue;
  @VssSignalMetadata about Vehicle_Powertrain_Transmission_GearChangeMode {
    path = "Vehicle.Powertrain.Transmission.GearChangeMode";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Is the gearbox in automatic or manual (paddle) mode.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Powertrain_Transmission_GearChangeMode {
    allowedValues = "MANUAL, AUTOMATIC";
  }

  attribute def Vehicle_Powertrain_Transmission_GearCount :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_Transmission_GearCount {
    path = "Vehicle.Powertrain.Transmission.GearCount";
    kind = "attribute";
    datatype = "int8";
    sourceDescription = "Number of forward gears in the transmission. -1 = CVT.";
    sourceComment = "";
  }

  attribute def Vehicle_Powertrain_Transmission_IsElectricalPowertrainEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Powertrain_Transmission_IsElectricalPowertrainEngaged {
    path = "Vehicle.Powertrain.Transmission.IsElectricalPowertrainEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is electrical powertrain mechanically connected/engaged to the drivetrain or not. False = Disconnected/Disengaged. True = Connected/Engaged.";
    sourceComment = "In some hybrid solutions it is possible to disconnect/disengage the electrical powertrain mechanically to avoid induced voltage reaching a too high level when driving at high speed.";
  }

  attribute def Vehicle_Powertrain_Transmission_IsLowRangeEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Powertrain_Transmission_IsLowRangeEngaged {
    path = "Vehicle.Powertrain.Transmission.IsLowRangeEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is gearbox in low range mode or not. False = Normal/High range engaged. True = Low range engaged.";
    sourceComment = "The possibility to switch between low and high gear range is typically only available in heavy vehicles and off-road vehicles.";
  }

  attribute def Vehicle_Powertrain_Transmission_IsParkLockEngaged :> Boolean;
  @VssSignalMetadata about Vehicle_Powertrain_Transmission_IsParkLockEngaged {
    path = "Vehicle.Powertrain.Transmission.IsParkLockEngaged";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "Is the transmission park lock engaged or not. False = Disengaged. True = Engaged.";
    sourceComment = "";
  }

  attribute def Vehicle_Powertrain_Transmission_PerformanceMode :> Vehicle_Powertrain_Transmission_PerformanceMode_AllowedValue;
  @VssSignalMetadata about Vehicle_Powertrain_Transmission_PerformanceMode {
    path = "Vehicle.Powertrain.Transmission.PerformanceMode";
    kind = "actuator";
    datatype = "string";
    sourceDescription = "Current gearbox performance mode.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Powertrain_Transmission_PerformanceMode {
    allowedValues = "NORMAL, SPORT, ECONOMY, SNOW, RAIN";
  }

  attribute def Vehicle_Powertrain_Transmission_SelectedGear :> Integer;
  @VssSignalMetadata about Vehicle_Powertrain_Transmission_SelectedGear {
    path = "Vehicle.Powertrain.Transmission.SelectedGear";
    kind = "actuator";
    datatype = "int8";
    sourceDescription = "The selected gear. 0=Neutral, 1/2/..=Forward, -1/-2/..=Reverse, 126=Park, 127=Drive.";
    sourceComment = "";
  }

  attribute def Vehicle_Powertrain_Transmission_Temperature :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_Transmission_Temperature {
    path = "Vehicle.Powertrain.Transmission.Temperature";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "The current gearbox temperature.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_Transmission_Temperature {
    quantityReference = "ISQ::thermodynamicTemperature";
    unitReference = "SI::degreeCelsius";
  }

  attribute def Vehicle_Powertrain_Transmission_TorqueDistribution :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_Transmission_TorqueDistribution {
    path = "Vehicle.Powertrain.Transmission.TorqueDistribution";
    kind = "actuator";
    datatype = "float";
    sourceDescription = "Torque distribution between front and rear axle in percent. -100% = Full torque to front axle, 0% = 50:50 Front/Rear, 100% = Full torque to rear axle.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_Transmission_TorqueDistribution {
    quantityReference = "ISQ::dimensionless";
    unitReference = "SI::percent";
  }
  @VssRangeMetadata about Vehicle_Powertrain_Transmission_TorqueDistribution {
    minValue = "-100";
    maxValue = "100";
  }

  attribute def Vehicle_Powertrain_Transmission_TravelledDistance :> Real;
  @VssSignalMetadata about Vehicle_Powertrain_Transmission_TravelledDistance {
    path = "Vehicle.Powertrain.Transmission.TravelledDistance";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Odometer reading, total distance travelled during the lifetime of the transmission.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Powertrain_Transmission_TravelledDistance {
    quantityReference = "ISQ::length";
    unitReference = "SI::kilometre";
  }

  attribute def Vehicle_Powertrain_Transmission_Type :> Vehicle_Powertrain_Transmission_Type_AllowedValue;
  @VssSignalMetadata about Vehicle_Powertrain_Transmission_Type {
    path = "Vehicle.Powertrain.Transmission.Type";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "Transmission type.";
    sourceComment = "";
  }
  @VssAllowedValuesMetadata about Vehicle_Powertrain_Transmission_Type {
    allowedValues = "UNKNOWN, SEQUENTIAL, H, AUTOMATIC, DSG, CVT";
  }

  attribute def Vehicle_Powertrain_Type :> Vehicle_Powertrain_Type_AllowedValue;
  @VssSignalMetadata about Vehicle_Powertrain_Type {
    path = "Vehicle.Powertrain.Type";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "Defines the powertrain type of the vehicle.";
    sourceComment = "For vehicles with a combustion engine (including hybrids) more detailed information on fuels supported can be found in FuelSystem.SupportedFuelTypes and FuelSystem.SupportedFuels.";
  }
  @VssAllowedValuesMetadata about Vehicle_Powertrain_Type {
    allowedValues = "COMBUSTION, HYBRID, ELECTRIC";
  }

  attribute def Vehicle_RoofLoad :> Integer;
  @VssSignalMetadata about Vehicle_RoofLoad {
    path = "Vehicle.RoofLoad";
    kind = "attribute";
    datatype = "int16";
    sourceDescription = "The permitted total weight of cargo and installations (e.g. a roof rack) on top of the vehicle.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_RoofLoad {
    quantityReference = "ISQ::mass";
    unitReference = "SI::kilogram";
  }

  attribute def Vehicle_Service_DistanceToService :> Real;
  @VssSignalMetadata about Vehicle_Service_DistanceToService {
    path = "Vehicle.Service.DistanceToService";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Remaining distance to service (of any kind). Negative values indicate service overdue.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Service_DistanceToService {
    quantityReference = "ISQ::length";
    unitReference = "SI::kilometre";
  }

  attribute def Vehicle_Service_IsServiceDue :> Boolean;
  @VssSignalMetadata about Vehicle_Service_IsServiceDue {
    path = "Vehicle.Service.IsServiceDue";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Indicates if vehicle needs service (of any kind). True = Service needed now or in the near future. False = No known need for service.";
    sourceComment = "";
  }

  attribute def Vehicle_Service_TimeToService :> Integer;
  @VssSignalMetadata about Vehicle_Service_TimeToService {
    path = "Vehicle.Service.TimeToService";
    kind = "sensor";
    datatype = "int32";
    sourceDescription = "Remaining time to service (of any kind). Negative values indicate service overdue.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Service_TimeToService {
    quantityReference = "ISQ::time";
    unitReference = "SI::second";
  }

  attribute def Vehicle_Speed :> Real;
  @VssSignalMetadata about Vehicle_Speed {
    path = "Vehicle.Speed";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Vehicle speed.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_Speed {
    quantityReference = "ISQ::speed";
    unitReference = "SI::kilometrePerHour";
  }

  attribute def Vehicle_StartTime :> String;
  @VssSignalMetadata about Vehicle_StartTime {
    path = "Vehicle.StartTime";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "Start time of current or latest trip, formatted according to ISO 8601 with UTC time zone.";
    sourceComment = "This signal is supposed to be set whenever a new trip starts. A new trip is considered to start when engine gets enabled (e.g. LowVoltageSystemState in ON or START mode). A trip is considered to end when engine is no longer enabled. The default value indicates that the vehicle never has been started, or that latest start time is unknown.";
  }
  @VssQuantityMetadata about Vehicle_StartTime {
    quantityReference = "n/a";
    unitReference = "ISO 8601 lexical date/time string";
  }

  attribute def Vehicle_Trailer_IsConnected :> Boolean;
  @VssSignalMetadata about Vehicle_Trailer_IsConnected {
    path = "Vehicle.Trailer.IsConnected";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "Signal indicating if trailer is connected or not.";
    sourceComment = "";
  }

  attribute def Vehicle_TraveledDistance :> Integer;
  @VssSignalMetadata about Vehicle_TraveledDistance {
    path = "Vehicle.TraveledDistance";
    kind = "sensor";
    datatype = "uint32";
    sourceDescription = "Odometer reading, total distance traveled during the lifetime of the vehicle.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_TraveledDistance {
    quantityReference = "ISQ::length";
    unitReference = "SI::metre";
  }

  attribute def Vehicle_TraveledDistanceSinceStart :> Integer;
  @VssSignalMetadata about Vehicle_TraveledDistanceSinceStart {
    path = "Vehicle.TraveledDistanceSinceStart";
    kind = "sensor";
    datatype = "uint32";
    sourceDescription = "Distance traveled since start of current trip.";
    sourceComment = "A new trip is considered to start when engine gets enabled (e.g. LowVoltageSystemState in ON or START mode). A trip is considered to end when engine is no longer enabled. The signal may however keep the value of the last trip until a new trip is started.";
  }
  @VssQuantityMetadata about Vehicle_TraveledDistanceSinceStart {
    quantityReference = "ISQ::length";
    unitReference = "SI::metre";
  }

  attribute def Vehicle_TripDuration :> Real;
  @VssSignalMetadata about Vehicle_TripDuration {
    path = "Vehicle.TripDuration";
    kind = "sensor";
    datatype = "float";
    sourceDescription = "Duration of latest trip.";
    sourceComment = "This signal is not assumed to be continuously updated, but instead set to 0 when a trip starts and set to the actual duration of the trip when a trip ends. A new trip is considered to start when engine gets enabled (e.g. LowVoltageSystemState in ON or START mode). A trip is considered to end when engine is no longer enabled.";
  }
  @VssQuantityMetadata about Vehicle_TripDuration {
    quantityReference = "ISQ::time";
    unitReference = "SI::second";
  }

  attribute def Vehicle_TripMeterReading :> Integer;
  @VssSignalMetadata about Vehicle_TripMeterReading {
    path = "Vehicle.TripMeterReading";
    kind = "actuator";
    datatype = "uint32";
    sourceDescription = "Trip meter reading.";
    sourceComment = "The trip meter is an odometer that can be manually reset by the driver";
  }
  @VssQuantityMetadata about Vehicle_TripMeterReading {
    quantityReference = "ISQ::length";
    unitReference = "SI::metre";
  }

  attribute def Vehicle_TurningDiameter :> Integer;
  @VssSignalMetadata about Vehicle_TurningDiameter {
    path = "Vehicle.TurningDiameter";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Minimum turning diameter, Wall-to-Wall, as defined by SAE J1100-2009 D102.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_TurningDiameter {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }

  attribute def Vehicle_VehicleIdentification_AcrissCode :> String;
  @VssSignalMetadata about Vehicle_VehicleIdentification_AcrissCode {
    path = "Vehicle.VehicleIdentification.AcrissCode";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "The ACRISS Car Classification Code is a code used by many car rental companies.";
    sourceComment = "";
  }

  attribute def Vehicle_VehicleIdentification_BodyType :> String;
  @VssSignalMetadata about Vehicle_VehicleIdentification_BodyType {
    path = "Vehicle.VehicleIdentification.BodyType";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "Indicates the design and body style of the vehicle (e.g. station wagon, hatchback, etc.).";
    sourceComment = "";
  }

  attribute def Vehicle_VehicleIdentification_Brand :> String;
  @VssSignalMetadata about Vehicle_VehicleIdentification_Brand {
    path = "Vehicle.VehicleIdentification.Brand";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "Vehicle brand or manufacturer.";
    sourceComment = "";
  }

  attribute def Vehicle_VehicleIdentification_DateVehicleFirstRegistered :> String;
  @VssSignalMetadata about Vehicle_VehicleIdentification_DateVehicleFirstRegistered {
    path = "Vehicle.VehicleIdentification.DateVehicleFirstRegistered";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "The date in ISO 8601 format of the first registration of the vehicle with the respective public authorities.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_VehicleIdentification_DateVehicleFirstRegistered {
    quantityReference = "n/a";
    unitReference = "ISO 8601 lexical date/time string";
  }

  attribute def Vehicle_VehicleIdentification_KnownVehicleDamages :> String;
  @VssSignalMetadata about Vehicle_VehicleIdentification_KnownVehicleDamages {
    path = "Vehicle.VehicleIdentification.KnownVehicleDamages";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "A textual description of known damages, both repaired and unrepaired.";
    sourceComment = "";
  }

  attribute def Vehicle_VehicleIdentification_LicensePlate :> String;
  @VssSignalMetadata about Vehicle_VehicleIdentification_LicensePlate {
    path = "Vehicle.VehicleIdentification.LicensePlate";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "The license plate of the vehicle.";
    sourceComment = "Depending on the context, this attribute might not be up to date or might be misconfigured, and therefore should be considered untrustworthy in the absence of another method of verification.";
  }

  attribute def Vehicle_VehicleIdentification_MeetsEmissionStandard :> String;
  @VssSignalMetadata about Vehicle_VehicleIdentification_MeetsEmissionStandard {
    path = "Vehicle.VehicleIdentification.MeetsEmissionStandard";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "Indicates that the vehicle meets the respective emission standard.";
    sourceComment = "";
  }

  attribute def Vehicle_VehicleIdentification_Model :> String;
  @VssSignalMetadata about Vehicle_VehicleIdentification_Model {
    path = "Vehicle.VehicleIdentification.Model";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "Vehicle model.";
    sourceComment = "";
  }

  attribute def Vehicle_VehicleIdentification_OptionalExtras :> String;
  @VssSignalMetadata about Vehicle_VehicleIdentification_OptionalExtras {
    path = "Vehicle.VehicleIdentification.OptionalExtras";
    kind = "attribute";
    datatype = "string[]";
    sourceDescription = "Optional extras refers to all car equipment options that are not installed as standard by the manufacturer.";
    sourceComment = "Allowed values are not standardized, each OEM can specify detail descriptions of array elements.";
  }

  attribute def Vehicle_VehicleIdentification_ProductionDate :> String;
  @VssSignalMetadata about Vehicle_VehicleIdentification_ProductionDate {
    path = "Vehicle.VehicleIdentification.ProductionDate";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "The date in ISO 8601 format of production of the item, e.g. vehicle.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_VehicleIdentification_ProductionDate {
    quantityReference = "n/a";
    unitReference = "ISO 8601 lexical date/time string";
  }

  attribute def Vehicle_VehicleIdentification_PurchaseDate :> String;
  @VssSignalMetadata about Vehicle_VehicleIdentification_PurchaseDate {
    path = "Vehicle.VehicleIdentification.PurchaseDate";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "The date in ISO 8601 format of the item e.g. vehicle was purchased by the current owner.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_VehicleIdentification_PurchaseDate {
    quantityReference = "n/a";
    unitReference = "ISO 8601 lexical date/time string";
  }

  attribute def Vehicle_VehicleIdentification_VIN :> String;
  @VssSignalMetadata about Vehicle_VehicleIdentification_VIN {
    path = "Vehicle.VehicleIdentification.VIN";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "17-character Vehicle Identification Number (VIN) as defined by ISO 3779.";
    sourceComment = "";
  }

  attribute def Vehicle_VehicleIdentification_VehicleConfiguration :> String;
  @VssSignalMetadata about Vehicle_VehicleIdentification_VehicleConfiguration {
    path = "Vehicle.VehicleIdentification.VehicleConfiguration";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "A short text indicating the configuration of the vehicle, e.g. '5dr hatchback ST 2.5 MT 225 hp' or 'limited edition'.";
    sourceComment = "";
  }

  attribute def Vehicle_VehicleIdentification_VehicleExteriorColor :> String;
  @VssSignalMetadata about Vehicle_VehicleIdentification_VehicleExteriorColor {
    path = "Vehicle.VehicleIdentification.VehicleExteriorColor";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "The main color of the exterior within the basic color palette (eg. red, blue, black, white, ...).";
    sourceComment = "";
  }

  attribute def Vehicle_VehicleIdentification_VehicleInteriorColor :> String;
  @VssSignalMetadata about Vehicle_VehicleIdentification_VehicleInteriorColor {
    path = "Vehicle.VehicleIdentification.VehicleInteriorColor";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "The color or color combination of the interior of the vehicle.";
    sourceComment = "";
  }

  attribute def Vehicle_VehicleIdentification_VehicleInteriorType :> String;
  @VssSignalMetadata about Vehicle_VehicleIdentification_VehicleInteriorType {
    path = "Vehicle.VehicleIdentification.VehicleInteriorType";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "The type or material of the interior of the vehicle (e.g. synthetic fabric, leather, wood, etc.).";
    sourceComment = "";
  }

  attribute def Vehicle_VehicleIdentification_VehicleModelDate :> String;
  @VssSignalMetadata about Vehicle_VehicleIdentification_VehicleModelDate {
    path = "Vehicle.VehicleIdentification.VehicleModelDate";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "The release date in ISO 8601 format of a vehicle model (often used to differentiate versions of the same make and model).";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_VehicleIdentification_VehicleModelDate {
    quantityReference = "n/a";
    unitReference = "ISO 8601 lexical date/time string";
  }

  attribute def Vehicle_VehicleIdentification_VehicleSeatingCapacity :> Integer;
  @VssSignalMetadata about Vehicle_VehicleIdentification_VehicleSeatingCapacity {
    path = "Vehicle.VehicleIdentification.VehicleSeatingCapacity";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "The number of passengers that can be seated in the vehicle, both in terms of the physical space available, and in terms of limitations set by law.";
    sourceComment = "";
  }

  attribute def Vehicle_VehicleIdentification_VehicleSpecialUsage :> String;
  @VssSignalMetadata about Vehicle_VehicleIdentification_VehicleSpecialUsage {
    path = "Vehicle.VehicleIdentification.VehicleSpecialUsage";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "Indicates whether the vehicle has been used for special purposes, like commercial rental, driving school.";
    sourceComment = "";
  }

  attribute def Vehicle_VehicleIdentification_WMI :> String;
  @VssSignalMetadata about Vehicle_VehicleIdentification_WMI {
    path = "Vehicle.VehicleIdentification.WMI";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "3-character World Manufacturer Identification (WMI) as defined by ISO 3780.";
    sourceComment = "";
  }

  attribute def Vehicle_VehicleIdentification_Year :> Integer;
  @VssSignalMetadata about Vehicle_VehicleIdentification_Year {
    path = "Vehicle.VehicleIdentification.Year";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Model year of the vehicle.";
    sourceComment = "";
  }

  attribute def Vehicle_VersionVSS_Label :> String;
  @VssSignalMetadata about Vehicle_VersionVSS_Label {
    path = "Vehicle.VersionVSS.Label";
    kind = "attribute";
    datatype = "string";
    sourceDescription = "Label to further describe the version.";
    sourceComment = "COVESA VSS project typically use dev for latest master, and empty string for released versions.";
  }

  attribute def Vehicle_VersionVSS_Major :> Integer;
  @VssSignalMetadata about Vehicle_VersionVSS_Major {
    path = "Vehicle.VersionVSS.Major";
    kind = "attribute";
    datatype = "uint32";
    sourceDescription = "Supported Version of VSS - Major version.";
    sourceComment = "";
  }

  attribute def Vehicle_VersionVSS_Minor :> Integer;
  @VssSignalMetadata about Vehicle_VersionVSS_Minor {
    path = "Vehicle.VersionVSS.Minor";
    kind = "attribute";
    datatype = "uint32";
    sourceDescription = "Supported Version of VSS - Minor version.";
    sourceComment = "";
  }

  attribute def Vehicle_VersionVSS_Patch :> Integer;
  @VssSignalMetadata about Vehicle_VersionVSS_Patch {
    path = "Vehicle.VersionVSS.Patch";
    kind = "attribute";
    datatype = "uint32";
    sourceDescription = "Supported Version of VSS - Patch version.";
    sourceComment = "";
  }

  attribute def Vehicle_WidthExcludingMirrors :> Integer;
  @VssSignalMetadata about Vehicle_WidthExcludingMirrors {
    path = "Vehicle.WidthExcludingMirrors";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Overall vehicle width excluding mirrors, as defined by SAE J1100-2009 W103.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_WidthExcludingMirrors {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }

  attribute def Vehicle_WidthFoldedMirrors :> Integer;
  @VssSignalMetadata about Vehicle_WidthFoldedMirrors {
    path = "Vehicle.WidthFoldedMirrors";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Overall vehicle width with mirrors folded, as defined by SAE J1100-2009 W145.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_WidthFoldedMirrors {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }

  attribute def Vehicle_WidthIncludingMirrors :> Integer;
  @VssSignalMetadata about Vehicle_WidthIncludingMirrors {
    path = "Vehicle.WidthIncludingMirrors";
    kind = "attribute";
    datatype = "uint16";
    sourceDescription = "Overall vehicle width including mirrors, as defined by SAE J1100-2009 W144.";
    sourceComment = "";
  }
  @VssQuantityMetadata about Vehicle_WidthIncludingMirrors {
    quantityReference = "ISQ::length";
    unitReference = "SI::millimetre";
  }

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
