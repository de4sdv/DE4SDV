package COVESA_VSS_EnumSmoke_PR2 {

  import ScalarValues::*;

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
    }

    metadata def VssSignalMetadata {
      :>> annotatedElement : SysML::AttributeDefinition;

      attribute path : String;
      attribute kind : VssSignalKind;
      attribute datatype : VssDatatype;
      attribute sourceDescription : String [0..1];
    }
  }

  package SignalDefinitions {
    import VssMetadata::*;

    enum def ActiveAutonomyLevelKind {
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

    attribute def Vehicle_ADAS_ActiveAutonomyLevel : ActiveAutonomyLevelKind {
      doc /* Indicates the currently active level of driving automation according to SAE J3016. */

      @VssSignalMetadata {
        path = "Vehicle.ADAS.ActiveAutonomyLevel";
        kind = VssSignalKind::sensor;
        datatype = VssDatatype::vssString;
        sourceDescription = "Indicates the currently active level of driving automation according to SAE J3016.";
      }
    }
  }
}
