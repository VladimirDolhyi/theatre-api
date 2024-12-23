import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from theatre.models import Play, Performance, TheatreHall, Genre, Actor
from theatre.serializers import PlayListSerializer, PlayDetailSerializer

PLAY_URL = reverse("theatre:play-list")
PERFORMANCE_URL = reverse("theatre:performance-list")


def sample_play(**params) -> Play:
    defaults = {
        "title": "Sample play",
        "description": "Sample description",
    }
    defaults.update(params)

    return Play.objects.create(**defaults)


def sample_genre(**params):
    defaults = {
        "name": "Drama",
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)

    return Actor.objects.create(**defaults)


def sample_performance(**params):
    theatre_hall = TheatreHall.objects.create(name="Blue", rows=20, seats_in_row=20)

    defaults = {
        "show_time": "2022-06-02 14:00:00",
        "play": None,
        "theatre_hall": theatre_hall,
    }
    defaults.update(params)

    return Performance.objects.create(**defaults)


def detail_url(play_id):
    return reverse("theatre:play-detail", args=[play_id])


def image_upload_url(play_id):
    """Return URL for recipe image upload"""
    return reverse("theatre:play-upload-image", args=[play_id])


class PlayImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.play = sample_play()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.performance = sample_performance(play=self.play)

    def tearDown(self):
        self.play.image.delete()

    def test_upload_image_to_play(self):
        """Test uploading an image to play"""
        url = image_upload_url(self.play.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.play.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.play.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.play.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_play_list(self):
        url = PLAY_URL
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                url,
                {
                    "title": "Title",
                    "description": "Description",
                    "genres": [1],
                    "actors": [1],
                    "image": ntf,
                },
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        play = Play.objects.get(title="Title")
        self.assertFalse(play.image)

    def test_image_url_is_shown_on_play_detail(self):
        url = image_upload_url(self.play.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_url(self.play.id))

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_play_list(self):
        url = image_upload_url(self.play.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(PLAY_URL)

        self.assertIn("image", res.data[0].keys())

    def test_image_url_is_shown_on_performance_detail(self):
        url = image_upload_url(self.play.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(PERFORMANCE_URL)

        self.assertIn("play_image", res.data[0].keys())


class UnauthenticatedPlayAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(PLAY_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)


class AuthenticatedPlayAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_plays_list(self):
        sample_play()
        play_with_genres = sample_play()

        genre_1 = sample_genre()
        genre2 = sample_genre(name="Action")

        play_with_genres.genres.add(genre_1, genre2)

        res = self.client.get(PLAY_URL)
        plays = Play.objects.all()
        serializer = PlayListSerializer(plays, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_plays_by_genres(self):
        play_without_genre = sample_play()
        play_with_genre1 = sample_play()
        play_with_genre2 = sample_play()

        genre_1 = sample_genre(name="Action")
        genre_2 = sample_genre(name="Adventure")

        play_with_genre1.genres.add(genre_1)
        play_with_genre2.genres.add(genre_2)

        res = self.client.get(
            PLAY_URL,
            {"genres": f"{genre_1.id},{genre_2.id}"}
        )

        serializer_without_genres = PlayListSerializer(play_without_genre)
        serializer_play_genre_1 = PlayListSerializer(play_with_genre1)
        serializer_play_genre_2 = PlayListSerializer(play_with_genre2)

        self.assertIn(serializer_play_genre_1.data, res.data)
        self.assertIn(serializer_play_genre_2.data, res.data)
        self.assertNotIn(serializer_without_genres, res.data)

    def test_filter_plays_by_actors(self):
        play_without_actor = sample_play()
        play_with_actor1 = sample_play()
        play_with_actor2 = sample_play()

        actor_1 = sample_actor(first_name="Bruce", last_name="Willis")
        actor_2 = sample_actor(first_name="Samuel", last_name="Jackson")

        play_with_actor1.actors.add(actor_1)
        play_with_actor2.actors.add(actor_2)

        res = self.client.get(
            PLAY_URL,
            {"actors": f"{actor_1.id},{actor_2.id}"}
        )

        serializer_without_actors = PlayListSerializer(play_without_actor)
        serializer_play_actor_1 = PlayListSerializer(play_with_actor1)
        serializer_play_actor_2 = PlayListSerializer(play_with_actor2)

        self.assertIn(serializer_play_actor_1.data, res.data)
        self.assertIn(serializer_play_actor_2.data, res.data)
        self.assertNotIn(serializer_without_actors, res.data)

    def test_filter_movies_by_title(self):
        play_without_title = sample_play()
        play_with_title1 = sample_play(title="The Departed")
        play_with_title2 = sample_play(title="Inception")

        res = self.client.get(
            PLAY_URL,
            {"title": "ep"}
        )

        serializer_without_title = PlayListSerializer(play_without_title)
        serializer_play_title_1 = PlayListSerializer(play_with_title1)
        serializer_play_title_2 = PlayListSerializer(play_with_title2)

        self.assertIn(serializer_play_title_1.data, res.data)
        self.assertIn(serializer_play_title_2.data, res.data)
        self.assertNotIn(serializer_without_title, res.data)

    def test_retrieve_play_detail(self):
        play = sample_play()
        play.genres.add(sample_genre())

        url = detail_url(play.id)

        res = self.client.get(url)

        serializer = PlayDetailSerializer(play)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_play(self):
        payload = {
            "title": "The Departed",
            "description": "Some description",
        }

        res = self.client.post(PLAY_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.test", password="testpassword", is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_play(self):
        payload = {
            "title": "The Departed",
            "description": "Some description",
        }

        res = self.client.post(PLAY_URL, payload)

        play = Play.objects.get(pk=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload.keys():
            self.assertEqual(payload[key], getattr(play, key))

    def test_create_play_with_genres(self):
        genre_1 = sample_genre(name="Action")
        genre_2 = sample_genre(name="Adventure")
        payload = {
            "title": "The Departed",
            "description": "Some description",
            "genres": [genre_1.id, genre_2.id],
        }

        res = self.client.post(PLAY_URL, payload)

        play = Play.objects.get(pk=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        genres = play.genres.all()
        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertEqual(genres.count(), 2)

    def test_create_play_with_actors(self):
        actor_1 = sample_actor(first_name="Bruce", last_name="Willis")
        actor_2 = sample_actor(first_name="Samuel", last_name="Jackson")
        payload = {
            "title": "The Departed",
            "description": "Some description",
            "actors": [actor_1.id, actor_2.id],
        }

        res = self.client.post(PLAY_URL, payload)

        play = Play.objects.get(pk=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        actors = play.actors.all()
        self.assertIn(actor_1, actors)
        self.assertIn(actor_2, actors)
        self.assertEqual(actors.count(), 2)

    def test_delete_play_allowed(self):
        play = sample_play()

        url = detail_url(play.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
