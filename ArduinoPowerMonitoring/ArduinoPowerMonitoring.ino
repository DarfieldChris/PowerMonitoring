//
// Power
//
// Monitor ACS765 current sensor and print instantaneous current 
// readings out on the serial port.
//
// Circuit:
//   The ACS765 circuit diagram is shown at:
//    http://www.darfieldearthship.com/measuring-power-consumption/ ‎
//
//   Vout from this circuit is connected to port A0 of an arduino uno
//

#include <MemoryFree.h>

uint16_t _val[175];          // An array to store a block of readings
uint8_t  _port;              // The analog port to monitor
uint16_t _valMin;            // minimum value from block of readings
uint16_t _valMax;            // maximum value from block of readings
     
float _Irms;                 // value of previous reading
unsigned long _timeIrms;     // time of previous reading

void setup() {
    _port = 0;
    _Irms = 0;
    _timeIrms = 0;
}



void loop () {  
   unsigned long timeStart, timeEnd;
   float val;

   // Set max and min readings to exceed smallest and largest
   // possible readings respectively
   _valMax = 0;
   _valMin = 2000;
   
   timeStart = millis();

   // read a block of readings
   // based on a 60 hz sinusoidal signal and the uno clock speed 
   // this loop will capture
   // more than one complete period of the signal
   for (int counter = 0; counter < sizeof(_val)/sizeof(_val[0]); counter++) { 
      _val[counter] = analogRead(_port);
      if (_val[counter] > _valMax) _valMax = _val[counter];
      if (_val[counter] < _valMin) _valMin = _val[counter];
   }
   
   timeEnd = millis();
   
   // The sensor has a zero point of approximately 2.5 volts and 
   // swings postively and negatively through this zero point.
   // Figure out the amplitude of this swing above or below zero
   val = (_valMax - _valMin)/2;
   
   // Go from raw sensor reading to peak voltage measured at sensor
   //     * assumes 5V power supply to Arduino
   //     * Vmeasured = (5V/1023 steps)*(peak steps measured)
   val = (5/1023)*val;
   
   // Go from this reading to Irms
   // Irms = Vmeasured*(1 amp/.040volts) * .707
   val = (val/.040)*.707;
  
   // report the result if more than 5 sec has passed or the signal has changed 
   if (val != _Irms || timeEnd - _timeIrms > 5000 )
   {
     // report the old reading
     Serial.print(_port);
     Serial.print(F(":"));
     Serial.print(_timeIrms);
     Serial.print(F(":"));
     Serial.print(timeStart);
     Serial.print(F(":"));
     Serial.print(_valMin);
     Serial.print(F(":"));
     Serial.print(_valMax);
     Serial.print(F(":"));
     Serial.println(_Irms);

     _Irms = val;
     _timeIrms = timeStart;
   }

   //DEBUG_PRINTLN(F("Elapsed time: "), timeEnd - timeStart);
}



