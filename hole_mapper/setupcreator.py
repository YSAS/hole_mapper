#!/usr/bin/env python
from flask import Flask, render_template, request, Response
from flask_wtf.csrf import CsrfProtect
from flask_wtf import Form
from wtforms import SelectMultipleField, SubmitField, BooleanField,RadioField
from wtforms import validators
from m2fs.plate.summarize import generate_tlist_file, generate_summary_file
import os
from glob import glob
import plate

app = Flask(__name__)
app.secret_key = 'development key'

@app.route('/', methods=['GET', 'POST'])
def index():

    if request.method == 'POST' and not request.form['reset']:
        if 'plate' in request.form:
            chosen_plate=request.form['plate']
            return render_template('setupselect.html', form=SetupSelectForm())
        
        if 'setup' in request.form:
            chosen_setup=request.form['setup']
            chosen_config=request.form['config']
            chosen_side=request.form['side']
            return render_template('awithselect.html', form=AWithSelectForm())
        
        if 'awith' in request.form:
            chosen_awith=request.form['awith']
            plug_img=generate_plugmap()
            return plug_img
        
    else:
        return render_template('plateselect.html', form=PlateSelectForm())


class PlateSelectForm(Form):
    plate = SelectField('Plate', validators=[validators.Required()])
    global _platedict
    _platedict=get_available_plate_names()
    plate.choices=_platedict.keys()
    reset = SubmitField("Reset")
    submit = SubmitField("Next")


class SetupSelectForm(Form):
    setup = SelectField('Setup', validators=[validators.Required()])
    config = SelectField('Config', validators=[validators.Required()])
    side = RadioButton('Side')
    setup.choices=get_setup_names_on_plate(chosen_plate)
    config.choices=get_available_config_names()
    side.choices=['Red', 'Blue', 'Any']
    reset = SubmitField("Reset")
    submit = SubmitField("Next")


class AWithSelectForm(Form):
    awith = SelectMultipleField('AssignWith',
                                validators=[validators.Required()])
    awith.choices=get_awith_setup_names(chosen_plate, chosen_setup)
    reset = SubmitField("Reset")
    submit = SubmitField("Generate Plugmap")


def get_available_plate_names():
    pnames={}
    files=glob(_plateDir+'*.plate')
    for file in files:
        if os.path.basename(file).lower() not in ['none.plate', 'sample.plate']:
            try:
                pnames[plate.Plate(file).name]=file
            except IOError:
                log.warning('Could not load {}. Skipping.')
    return pnames

def get_setup_names_on_plate(platename):

    return setup_names

def get_available_config_names():
    return config_names

def get_awith_setup_names(platename, setupname):
    pass

def generate_plugmap():
    pass

if __name__ =='__main__':
    #configure paths
    holemapper_pathconf.ROOT=root_dir

    #Start web interface
    app.run(debug=True)



#Page to select plate
#page to select setup, config, & Side
#page to select awith setups, config & side
#generate plugdef

