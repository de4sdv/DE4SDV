package GateAPLEMLFixture {
    private import PLEML::*;

    #featureModel occurrence def GateAFeatureModel {
        doc /* Synthetic Gate A fixture. It proves representation and API
             * observability only; it does not define the DE4SDV portfolio. */

        #featureTree occurrence gateAFeatureTree :> featureTrees {
            #feature occurrence application[1];
            #feature occurrence autoware[0..1] :> application default null;
            #feature occurrence apollo[0..1] :> application default null {
                assert constraint :>> xorFeatures {
                    in #feature occurrence :>> excluded = (androidSDV);
                }
            }
            #feature occurrence openpilot[0..1] :> application default null {
                assert constraint :>> requiresFeatures {
                    in #feature occurrence :>> requiredFeatures = (diagnostics);
                }
            }

            #feature occurrence middleware[1];
            #feature occurrence androidSDV[0..1] :> middleware default null;
            #feature occurrence eclipseSCORE[0..1] :> middleware default null;
            #feature occurrence noVehicleMiddleware[0..1] :> middleware default null;

            #feature occurrence diagnostics[0..1] default null;
            #feature occurrence remoteDiagnostics[0..1] default null {
                attribute :>> bindingTime = LifeCycleKind::Production;
            }

            doc /* At-least-one / multi-select group probe. sensorSuite owns
                 * radar and camera as independent features; sensorSuite[1..*]
                 * requires at least one selected member and permits many.
                 * upper = * models the unbounded upper bound. */
            #feature occurrence sensorSuite[1..*];
            #feature occurrence radar[0..1] :> sensorSuite default null;
            #feature occurrence camera[0..1] :> sensorSuite default null;
        }

        #featureConfiguration occurrence validAutowareAndroid
            :> gateAFeatureTree, featureConfigurations {
            #feature occurrence :>> application[1] = (autoware);
            #feature occurrence :>> autoware[1];
            #feature occurrence :>> middleware[1] = (androidSDV);
            #feature occurrence :>> androidSDV[1];
        }

        #featureConfiguration occurrence validAutowareSCORE
            :> gateAFeatureTree, featureConfigurations {
            #feature occurrence :>> application[1] = (autoware);
            #feature occurrence :>> autoware[1];
            #feature occurrence :>> middleware[1] = (eclipseSCORE);
            #feature occurrence :>> eclipseSCORE[1];
        }

        #featureConfiguration occurrence validAutowareNoMiddleware
            :> gateAFeatureTree, featureConfigurations {
            #feature occurrence :>> application[1] = (autoware);
            #feature occurrence :>> autoware[1];
            #feature occurrence :>> middleware[1] = (noVehicleMiddleware);
            #feature occurrence :>> noVehicleMiddleware[1];
        }

        #featureConfiguration occurrence forbiddenApolloAndroid
            :> gateAFeatureTree, featureConfigurations {
            #feature occurrence :>> application[1] = (apollo);
            #feature occurrence :>> apollo[1];
            #feature occurrence :>> middleware[1] = (androidSDV);
            #feature occurrence :>> androidSDV[1];
        }

        #featureConfiguration occurrence missingOpenpilotSCORE
            :> gateAFeatureTree, featureConfigurations {
            #feature occurrence :>> application[1] = (openpilot);
            #feature occurrence :>> openpilot[1];
            #feature occurrence :>> middleware[1] = (eclipseSCORE);
            #feature occurrence :>> eclipseSCORE[1];
            #feature occurrence :>> diagnostics[1];
        }

        #featureConfiguration occurrence validBothSensors
            :> gateAFeatureTree, featureConfigurations {
            doc /* Multi-select proof: both sensorSuite members resolve. */
            #feature occurrence :>> sensorSuite[1..*] = (radar, camera);
            #feature occurrence :>> radar[1];
            #feature occurrence :>> camera[1];
        }

        #featureConfiguration occurrence validOneSensor
            :> gateAFeatureTree, featureConfigurations {
            doc /* At-least-one proof: exactly one sensorSuite member resolves. */
            #feature occurrence :>> sensorSuite[1..*] = (radar);
            #feature occurrence :>> radar[1];
        }

        #featureConfiguration occurrence invalidNoSensor
            :> gateAFeatureTree, featureConfigurations {
            doc /* At-least-one violation probe: the group resolves with no
                 * member. The Gate A evaluator treats empty group resolution
                 * as configuration-invalid; complete cardinality validation
                 * remains production evaluator work. */
            #feature occurrence :>> sensorSuite[1..*];
        }
    }

    part def GateACommonCoreCapability;

    part def GateASharedAssets {
        variation part gateAAdapterVariation {
            variant part autowareToAAOSSDV;
            variant part autowareToSCORE;
            variant part apolloToSCORE;
        }
        part gateASimpleBoundAsset;
    }

    constraint def NativeAdapterImplicationProbe {
        in occurrence selectedApplication : PLEML::Feature;
        in occurrence selectedMiddleware : PLEML::Feature;
        in occurrence selectedAdapter;
        in occurrence requiredApplication : PLEML::Feature;
        in occurrence requiredMiddleware : PLEML::Feature;
        in occurrence requiredAdapter;

        (selectedApplication == requiredApplication
            and selectedMiddleware == requiredMiddleware)
            implies selectedAdapter == requiredAdapter
    }

    occurrence def AdapterRealizationRule {
        doc /* Both requiredApplication and requiredMiddleware form one explicit
             * conjunction. A missing resultingAdapter means that this matched
             * combination explicitly requires no adapter. */
        in occurrence requiredApplication : PLEML::Feature;
        in occurrence requiredMiddleware : PLEML::Feature;
        in occurrence resultingAdapter[0..1];
    }

    occurrence def AdapterRuleSet;

    occurrence nominalAdapterRules : AdapterRuleSet {
        occurrence autowareAndroidRule : AdapterRealizationRule {
            in occurrence :>> requiredApplication =
                GateAFeatureModel::gateAFeatureTree::autoware;
            in occurrence :>> requiredMiddleware =
                GateAFeatureModel::gateAFeatureTree::androidSDV;
            in occurrence :>> resultingAdapter =
                GateASharedAssets::gateAAdapterVariation::autowareToAAOSSDV;
        }

        occurrence autowareSCORERule : AdapterRealizationRule {
            in occurrence :>> requiredApplication =
                GateAFeatureModel::gateAFeatureTree::autoware;
            in occurrence :>> requiredMiddleware =
                GateAFeatureModel::gateAFeatureTree::eclipseSCORE;
            in occurrence :>> resultingAdapter =
                GateASharedAssets::gateAAdapterVariation::autowareToSCORE;
        }

        occurrence autowareNoMiddlewareRule : AdapterRealizationRule {
            in occurrence :>> requiredApplication =
                GateAFeatureModel::gateAFeatureTree::autoware;
            in occurrence :>> requiredMiddleware =
                GateAFeatureModel::gateAFeatureTree::noVehicleMiddleware;
        }
    }

    occurrence ambiguousAdapterRules : AdapterRuleSet {
        occurrence ambiguousAndroidRuleA : AdapterRealizationRule {
            in occurrence :>> requiredApplication =
                GateAFeatureModel::gateAFeatureTree::autoware;
            in occurrence :>> requiredMiddleware =
                GateAFeatureModel::gateAFeatureTree::androidSDV;
            in occurrence :>> resultingAdapter =
                GateASharedAssets::gateAAdapterVariation::autowareToAAOSSDV;
        }
        occurrence ambiguousAndroidRuleB : AdapterRealizationRule {
            in occurrence :>> requiredApplication =
                GateAFeatureModel::gateAFeatureTree::autoware;
            in occurrence :>> requiredMiddleware =
                GateAFeatureModel::gateAFeatureTree::androidSDV;
            in occurrence :>> resultingAdapter =
                GateASharedAssets::gateAAdapterVariation::autowareToSCORE;
        }
    }

    occurrence gateAProject {
        #featureModel occurrence gateAFeatureModel : GateAFeatureModel;

        doc /* gateACommonCoreAsset sits outside the feature tree and outside
             * every configuration. That placement alone does not classify it
             * as common: real common/variable portfolio classification and its
             * SysML representation are established in Gate C from the real
             * scope baseline. Gate A proves only the "common capability
             * outside feature tree" evidence concept. */
        part gateACommonCoreAsset : GateACommonCoreCapability;
        part gateASharedAssets : GateASharedAssets;

        #FeatureBinding dependency gateASimpleFeatureBinding
            from gateASharedAssets::gateASimpleBoundAsset
            to gateAFeatureModel::gateAFeatureTree::autoware;
    }
}
