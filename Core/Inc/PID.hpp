#pragma once

static double clamp(double value, double min, double max) {
    if (value < min) return min;
    if (value > max) return max;
    return value;
}

class PID {
public:
    PID(double dt, double max, double min, double Kp, double Ki, double Kd, double Tf) :
        _dt(dt), _max(max), _min(min), _Kp(Kp), _Ki(Ki), _Kd(Kd), _Tf(Tf), _pre_error(0), _integral(0)
    {
    	_Tt = _Kp / _Ki;
        alpha = _Tf / (_Tf + _dt);
        pre_D = 0;
        es = 0;
    }

    double calculate(double yr, double y) {
        
        double error = yr - y;
        // ze względu na zasilanie o niskim napięciu
        // dla uchybu poniżej 20% będzie działał jako dwu położeniowy
        // dla testowania ułatwi nam to życie
        if(error *0.8 < error)
        	if(error > 0 ) return _max;
        		else return _min;

        double P = _Kp * error; // P 

        _integral += error * _dt;
        double I = (es / _Tt + _Ki)*_integral; // I

        double derivative = (error - _pre_error) / _dt;
        double D = (alpha * pre_D) + ( (1 - alpha)*_Kd * derivative / _dt ); // D with filter
        pre_D = D;

        double v = P+I+D;
        double u = clamp(v, _min, _max); // saturation

        es = v - u; // filter I 

        _pre_error = error;

        return u;
    }

    double getError() const { return _pre_error; }
    void reset() {
        _pre_error = 0;
        _integral = 0;
        pre_D = 0;
        es = 0;
    }

private:
    double _dt;
    double _max;
    double _min;
    double _Kp;
    double _Ki;
    double _Kd;
    double _Tf;
    double _Tt;
    double _pre_error;
    double _integral;
    double alpha;
    double pre_D;
    double es; 
};

