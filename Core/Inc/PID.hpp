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
        double P = _Kp * error; // P 

        double bi = _Ki * error * _dt;
        double tr = 0.0;

            if (_Tf > 0.0)
                tr = (es / _Tf) * _dt;

        _integral += bi + tr;
        double I = _integral;

        double derivative = (error - _pre_error) / _dt;
        double D = (alpha * pre_D) + ( (1 - alpha)*_Kd * derivative ); // D with filter
        pre_D = D;

        double v = P+I+D;
        double u = clamp(v, _min, _max); // saturation

        es = u - v; // filter I

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

