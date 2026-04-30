"""Academics - Serializers"""
from rest_framework import serializers
from academics.models import (
    AcademicSession, Group, Category, Subject, SubjectSection,
    Chapter, Topic, Batch, Users, BatchTeacher,
    Language, State, City, Religion, School,
)


class AcademicSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicSession
        fields = '__all__'
        read_only_fields = ('id',)


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = '__all__'
        read_only_fields = ('id',)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'
        read_only_fields = ('id',)


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = '__all__'
        read_only_fields = ('id',)


class SubjectSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubjectSection
        fields = '__all__'
        read_only_fields = ('id',)


class ChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = '__all__'
        read_only_fields = ('id',)


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = '__all__'
        read_only_fields = ('id',)


class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class UsersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        exclude = ('password',)
        read_only_fields = ('id',)


class BatchTeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = BatchTeacher
        fields = '__all__'
        read_only_fields = ('id',)


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = '__all__'
        read_only_fields = ('id',)


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = '__all__'
        read_only_fields = ('id',)


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = '__all__'
        read_only_fields = ('id',)


class ReligionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Religion
        fields = '__all__'
        read_only_fields = ('id',)


class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = '__all__'
        read_only_fields = ('id',)
