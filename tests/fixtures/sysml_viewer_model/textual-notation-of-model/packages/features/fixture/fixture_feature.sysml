/*
 * Synthetic fixture for the SysML HTML viewer tests.
 * Hand-authored test data — NOT a copy of any real DE4SDV model file.
 */

package FixtureRoot {
  part def RootLevelPart;

  package Features {
    package FixtureFeature {
      private import Views::*;

      part def FixtureSystem {
        doc /* A synthetic system part definition for viewer tests. */
        port signalIn : SignalInputPort;
        port signalOut : SignalOutputPort;
      }

      part fixtureSystem : FixtureSystem;

      part 'quoted part' : FixtureSystem;

      part importedPart : FixtureSharedType;

      requirement fixtureRequirement {
        doc /* Synthetic requirement: the fixture must render. */
        id "FIX-001";
        text "The fixture renders in the viewer.";
      }

      concern fixtureStructureConcern;

      concern fixtureAdjacentConcern {
        require constraint {
          doc /* Constraint doc: must NOT leak onto the next concern. */
        }
      }

      concern fixtureTargetConcern {
        doc /* The real doc of the target concern, with a
             * second line. */
      }

      view fixtureStructureView {
        doc /* Synthetic structure view for render tests. */
        viewpoint selectedFixtureViewpoint : FixtureViewpoint {
          concern fixtureStructureConcern;
        }
        frame fixtureStructureConcern;
        expose FixtureSystem;
        render asTreeDiagram;
      }

      view fixtureMatrixView : MVD::MatrixView {
        viewpoint selectedMatrixViewpoint : FixtureViewpoint {
          concern fixtureStructureConcern;
        }
        frame fixtureStructureConcern;
        expose FixtureSystem::*;
      }

      abstract part def FixtureAbstractPart;

      dependency fixtureDependency from fixtureSystem to fixtureRequirement;
      stakeholder fixtureStakeholder : SystemsEngineer;
    }
  }
}
