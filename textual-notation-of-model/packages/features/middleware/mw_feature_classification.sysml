/*
 * DE4SDV middleware feature/common-capability classification model slice.
 *
 * INC-MW-003 classifies each middleware integration element as a feature,
 * common capability, constraint, or evidence capability per the DE4SDV
 * feature/common-capability rule (ISO/IEC 26580-aligned). It records variation
 * points from the SDV platform stack and confirms the classification hypothesis
 * from INC-MW-002.
 *
 * This increment does NOT define requirements, functional behavior, logical
 * architecture, or physical/software realization.
 */

package DE4SDV_MWFeatureClassification {
  package Features {
    package Middleware {
      package FeatureClassification {
        private import Views::*;
        private import DE4SDV_Stakeholders::*;
        private import DE4SDV_ProductLine::*;
        private import DE4SDV_MethodViewpoints::*;
        private import SAF_Viewpoints::*;

        /*
         * Classification concern: reviewers need to see common capabilities
         * separated from features and variation points.
         */
        concern productLineCapabilityClassificationConcern : ProductLineCapabilityClassificationConcern {
          doc /*
           * Reviewers need middleware scope elements to distinguish common
           * product-line capabilities from features, candidate features,
           * and variation points before downstream functional modeling
           * starts.
           */
          subject;
          stakeholder productLineEngineer : ProductLineEngineer;
          stakeholder systemsEngineer : SystemsEngineer;
          stakeholder reviewer : OpenSourceReviewer;
        }

        /*
         * Common capabilities — required for any app+middleware combination.
         * Not features: they do not distinguish member products.
         */
        part adapterLayer : CommonProductLineCapability {
          doc /*
           * The application-middleware adapter layer is a common capability.
           * Every (application, middleware) pair requires an adapter to
           * translate between incompatible communication paradigms
           * (ROS 2/DDS vs VSIDL/LoLa/SOME/IP). The adapter does not
           * distinguish member products — it is present whenever middleware
           * is not "none" and absent when it is.
           */
        }

        part signalAccessCapability : CommonProductLineCapability {
          doc /*
           * The capability to exchange vehicle signals through the
           * middleware is a common capability. It is required whenever
           * an ADAS application and a vehicle-level middleware are both
           * selected.
           */
        }

        part lifecycleCoordinationCapability : CommonProductLineCapability {
          doc /*
           * Lifecycle coordination (startup, shutdown, suspend, resume)
           * through the middleware is a common capability. It does not
           * distinguish member products.
           */
        }

        part healthMonitoringCapability : CommonProductLineCapability {
          doc /*
           * Health monitoring and fault detection through the middleware
           * is a common capability. It is required for all middleware-
           * integrated products.
           */
        }

        part diagnosticAccessCapability : CommonProductLineCapability {
          doc /*
           * Authenticated diagnostic access through the middleware is a
           * common capability. It does not distinguish member products.
           */
        }

        part updateCoordinationCapability : CommonProductLineCapability {
          doc /*
           * OTA software update coordination through the middleware is a
           * common capability. It does not distinguish member products.
           */
        }

        /*
         * The adapter variant follows from the (application, middleware)
         * pair. It is not an independent feature — it is a derived
         * consequence of the two feature selections.
         */
        part adapterVariantDerivation : CommonProductLineCapability {
          doc /*
           * The adapter variant is derived from the (application,
           * middleware) feature pair, not selected independently. For
           * example: (Autoware, AAOS SDV) -> AutowareToAAOSSDVAdapter.
           * This is a common capability because the adapter is always
           * needed when middleware is present — the specific adapter
           * follows from the feature combination.
           */
        }

        /*
         * Features are not modeled as SysML elements here. They are
         * variation points in the SDV platform stack (middleware layer,
         * vehicle application layer) and are managed in the YAML feature
         * model. The classification decision is recorded in the YAML
         * framing file. The parts below are descriptive references to
         * those variation points for review traceability.
         */
        part middlewareVariationPoint : ProductLineVariantChoice {
          doc /*
           * Feature: middleware platform selection. Variation point:
           * middleware layer in the SDV platform stack. Variants:
           * Eclipse S-CORE, Android SDV, AUTOSAR Adaptive, none.
           * Located in DE4SDV_SDVPlatformStack. Managed in YAML.
           */
        }

        part applicationVariationPoint : ProductLineVariantChoice {
          doc /*
           * Feature: application stack selection. Variation point:
           * vehicle application layer in the SDV platform stack.
           * Variants: Autoware, OpenPilot, Apollo. Located in
           * DE4SDV_SDVPlatformStack. Managed in YAML.
           */
        }

        part adapterVariationPoint : ProductLineVariantChoice {
          doc /*
           * Derived variation point: application-middleware adapter layer
           * in the SDV platform stack. Variants follow from (application,
           * middleware) pair: AutowareToSCORE, AutowareToAAOSSDV,
           * AutowareToAUTOSAR, OpenpilotToSCORE, ApolloToSCORE, none.
           * Located in DE4SDV_SDVPlatformStack. Managed in YAML.
           */
        }

        /*
         * Deferred scope — not classified in this increment.
         */
        part safetyPathDecision : DeferredProductLineScope {
          doc /*
           * The decision about which emergency intervention path to
           * realize (through safety-certified middleware partition vs
           * direct vehicle-command gate) is deferred to INC-MW-004
           * (needs) and INC-MW-005 (requirements).
           */
        }

        part securityTrustBoundary : DeferredProductLineScope {
          doc /*
           * The security and trust boundary for middleware communication
           * (DICE identity, attestation, VLAN segmentation) is not yet
           * classified. Deferred to a security-focused increment or
           * INC-MW-005.
           */
        }

        /*
         * View
         */
        view mwProductLineClassificationView {
          viewpoint selectedProductLineClassificationViewpoint : ProductLineClassificationViewpoint {
            frame productLineCapabilityClassificationConcern;
          }

          expose FeatureClassification::*;
          render asTreeDiagram;
        }
      }
    }
  }
}
