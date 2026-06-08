package COVESA_VSS_MetadataSmoke_PR1 {

  import ScalarValues::*;
  import ISQ::*;
  import SI::*;
  import USCustomaryUnits::*;

  package VssMetadata {
    enum def VssSignalKind {
      sensor;
      actuator;
      attribute;
      branch;
    }

    enum def VssDatatype {
      vssBoolean;
      vssString;
      vssFloat;
      vssUint8;
      vssUint16;
      vssInt32;
      vssUint32;
    }

    metadata def VssSignalMetadata {
      :>> annotatedElement : SysML::AttributeDefinition;

      attribute path : String;
      attribute kind : VssSignalKind;
      attribute datatype : VssDatatype;
      attribute sourceDescription : String [0..1];
    }

    metadata def VssQuantityMetadata {
      :>> annotatedElement : SysML::AttributeDefinition;

      attribute quantityReference : String [0..1];
      attribute unitReference : String [0..1];
    }

    metadata def VssRangeMetadata {
      :>> annotatedElement : SysML::AttributeDefinition;

      attribute minValue : Real [0..1];
      attribute maxValue : Real [0..1];
    }
  }

  package SignalDefinitions {
    import VssMetadata::*;

    attribute def Vehicle_ADAS_ABS_IsEnabled : Boolean {
      doc /* Indicates if ABS is enabled. True = Enabled. False = Disabled. */

      @VssSignalMetadata {
        path = "Vehicle.ADAS.ABS.IsEnabled";
        kind = VssSignalKind::actuator;
        datatype = VssDatatype::vssBoolean;
        sourceDescription = "Indicates if ABS is enabled. True = Enabled. False = Disabled.";
      }
    }

    attribute def Vehicle_ADAS_CruiseControl_AdaptiveDistanceSet : Real {
      doc /* Distance in meters to keep from lead vehicle. */

      @VssSignalMetadata {
        path = "Vehicle.ADAS.CruiseControl.AdaptiveDistanceSet";
        kind = VssSignalKind::actuator;
        datatype = VssDatatype::vssFloat;
        sourceDescription = "Distance in meters to keep from lead vehicle.";
      }

      @VssQuantityMetadata {
        quantityReference = "ISQ::length";
        unitReference = "SI::metre";
      }

      @VssRangeMetadata {
        minValue = 0.0;
      }
    }
  }
}
