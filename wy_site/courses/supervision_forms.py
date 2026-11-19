from django import forms

from .models import Course, StudyTask, Submission


class TaskForm(forms.ModelForm):
    class Meta:
        model = StudyTask
        fields = ['course', 'title', 'instructions', 'due_at']
        widgets = {
            'course': forms.Select(attrs={'class': 'input'}),
            'title': forms.TextInput(attrs={'class': 'input'}),
            'instructions': forms.Textarea(attrs={'class': 'input', 'rows': 5}),
            'due_at': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M', attrs={'class': 'input', 'type': 'datetime-local'},
            ),
        }

    def __init__(self, *args, courses, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['course'].queryset = courses


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['content', 'recognized_text', 'difficulties']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'input', 'rows': 5}),
            'recognized_text': forms.Textarea(attrs={'class': 'input', 'rows': 4}),
            'difficulties': forms.Textarea(attrs={'class': 'input', 'rows': 3}),
        }


class ReviewForm(forms.Form):
    feedback = forms.CharField(
        label='教师反馈', max_length=3000, widget=forms.Textarea(attrs={'class': 'input', 'rows': 5}),
    )
    action = forms.ChoiceField(choices=[('review', '发布反馈'), ('return', '退回重交')])
    version = forms.CharField(max_length=40, required=False, widget=forms.HiddenInput)

    def __init__(self, *args, submission, **kwargs):
        super().__init__(*args, initial={'version': submission.submitted_at.isoformat()}, **kwargs)

    def clean(self):
        cleaned = super().clean()
        if 'action' not in cleaned:
            raise forms.ValidationError('请选择发布反馈或退回重交。')
        if cleaned.get('version') and cleaned['version'] != self.initial['version']:
            raise forms.ValidationError('学生已重新提交，请刷新后查看最新内容。')
        return cleaned


class RecommendationForm(forms.Form):
    recognized_text = forms.CharField(max_length=2000, required=False)
    difficulties = forms.CharField(max_length=2000, required=False)


class DraftForm(forms.Form):
    review_points = forms.CharField(max_length=2000)
