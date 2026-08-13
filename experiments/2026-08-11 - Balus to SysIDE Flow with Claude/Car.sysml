package CarTestModel {

     
    view 'Car Interconnection View' : StandardViewDefinitions::InterconnectionView {
        expose 'car'::'drivetrain';
        expose 'car'::'drivetrain'::'engine'::'crankshaft';
        expose 'car'::'drivetrain'::'alternator';
        expose 'car'::'drivetrain'::'battery';
    }    


    item def Torque;
    item def Electricity;

    part car {
        part drivetrain {
            part engine {
                part crankshaft {
                    out item torqueOut : Torque;
                }
            }
            part alternator {
                in item torqueIn : Torque;
                out item electricityOut : Electricity;
            }
            part battery {
                in item electricityIn : Electricity;
            }

            flow engine.crankshaft.torqueOut to alternator.torqueIn;
            flow alternator.electricityOut to battery.electricityIn;
        }
        part body;
        part wheels;
    }

}
