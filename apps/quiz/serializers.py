from rest_framework import serializers


class StartSessionSerializer(serializers.Serializer):
    category = serializers.SlugField(help_text="Kategori slug'ı")


class SessionCreatedSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    category = serializers.CharField()
    question_count = serializers.IntegerField()


class ChoiceOutSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    text = serializers.CharField()


class QuestionOutSerializer(serializers.Serializer):
    position = serializers.IntegerField()
    total_questions = serializers.IntegerField()
    text = serializers.CharField()
    choices = ChoiceOutSerializer(many=True)
    time_limit_ms = serializers.IntegerField()
    remaining_ms = serializers.IntegerField()


class AnswerInSerializer(serializers.Serializer):
    question_position = serializers.IntegerField(min_value=1)
    choice_id = serializers.IntegerField(allow_null=True, help_text="Süre dolduysa null")


class AnswerOutSerializer(serializers.Serializer):
    is_correct = serializers.BooleanField()
    correct_choice_id = serializers.IntegerField()
    score_gained = serializers.IntegerField()
    finished = serializers.BooleanField(help_text="Son soru cevaplandıysa true")


class ResultSerializer(serializers.Serializer):
    category = serializers.CharField()
    total_score = serializers.IntegerField()
    correct_count = serializers.IntegerField()
    question_count = serializers.IntegerField()
    total_time_ms = serializers.IntegerField()
    score_submitted = serializers.BooleanField()


class SubmitScoreInSerializer(serializers.Serializer):
    player_name = serializers.CharField(max_length=100)


class SubmitScoreOutSerializer(serializers.Serializer):
    entry_id = serializers.IntegerField()
    rank = serializers.IntegerField()
    player_name = serializers.CharField()
    score = serializers.IntegerField()
