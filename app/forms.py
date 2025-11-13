from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    BooleanField,
    SubmitField,
    TextAreaField,
    FileField,
    SelectField,
)
from wtforms.validators import DataRequired, EqualTo, Length, ValidationError
from flask_babel import lazy_gettext as _l
from app.models import User

ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'flac', 'm4a'}


def allowed_file(filename, allowed_extensions):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


class LoginForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired()])
    password = PasswordField(_l('Password'), validators=[DataRequired()])
    remember_me = BooleanField(_l('Remember Me'))
    submit = SubmitField(_l('Sign In'))


class RegistrationForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired(), Length(min=2, max=64)])
    email = StringField(_l('Email'), validators=[DataRequired(), Length(max=120)])
    password = PasswordField(_l('Password'), validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField(
        _l('Repeat Password'),
        validators=[DataRequired(), EqualTo('password')]
    )
    submit = SubmitField(_l('Register'))

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError(_l('Please use a different username.'))

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError(_l('Please use a different email address.'))


class SongUploadForm(FlaskForm):
    title = StringField(_l('Song Title'), validators=[DataRequired(), Length(max=100)])
    artist = StringField(_l('Artist'), validators=[DataRequired(), Length(max=100)])
    album = StringField(_l('Album'), validators=[Length(max=100)])
    genre = StringField(_l('Genre'), validators=[Length(max=50)])
    visibility = SelectField(_l('Visibility'), choices=[
        ('public', _l('Public - Share with everyone')),
        ('private', _l('Private - Only visible to me'))
    ], default='public')
    audio_file = FileField(_l('Audio File'), validators=[DataRequired()])
    cover_image = FileField(_l('Cover Image (optional)'))
    auto_search_cover = BooleanField(_l('Auto search cover online'))
    submit = SubmitField(_l('Upload Song'))

    def validate_audio_file(self, audio_file):
        if audio_file.data and audio_file.data.filename:
            if not allowed_file(audio_file.data.filename, ALLOWED_AUDIO_EXTENSIONS):
                raise ValidationError(_l('Please select a valid audio file (MP3, WAV, OGG, FLAC, M4A).'))


class PlaylistForm(FlaskForm):
    name = StringField(_l('Playlist Name'), validators=[DataRequired()])
    description = TextAreaField(_l('Description'))
    visibility = SelectField(_l('Visibility'), choices=[
        ('public', _l('Public - Share with everyone')),
        ('private', _l('Private - Only visible to me'))
    ], default='public')
    submit = SubmitField(_l('Create Playlist'))


class CommentForm(FlaskForm):
    content = TextAreaField(_l('Comment'), validators=[DataRequired(), Length(max=500)])
    submit = SubmitField(_l('Post Comment'))


class ProfileForm(FlaskForm):
    bio = TextAreaField(_l('Bio'), validators=[Length(max=500)])
    location = StringField(_l('Location'), validators=[Length(max=100)])
    website = StringField(_l('Website'), validators=[Length(max=200)])
    avatar = FileField(_l('Profile Picture'))
    submit = SubmitField(_l('Update Profile'))
