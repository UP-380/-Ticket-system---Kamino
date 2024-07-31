from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateField, SelectField
from wtforms.validators import DataRequired

class Filtro(FlaskForm):
    empresa = SelectField('Empresa', choices=[('up380', 'Up380'), ('unymos', 'Unymos')], validators=[DataRequired()])
    data_inicial = DateField('Data Inicial', format='%Y-%m-%d', validators=[DataRequired()])
    data_final = DateField('Data Final', format='%Y-%m-%d', validators=[DataRequired()])
    pesquisar = SubmitField('Buscar')
