"""Example Prestodoctor mappings for the internal database."""

class PrestodoctorMapper(EmailSocialLoginMapper):
    """Map Prestodoctor external users to our database."""

    def import_social_media_user(self, user):
        """Convert incoming Authomatic object to info dictionary."""

        # Merge all separate data sources to a single dictionary
        info = user.base_data.copy()
        info["photo_id"] = user.photo_data.copy()
        info["recommendation"] = user.recommendation_data.copy()
        return info

    def update_first_login_social_data(self, user, data):
        """Update user full name on the first login only."""
        super(PrestodoctorMapper, self).update_first_login_social_data(user, data)
        user.full_name = data["first_name"] + " " + data["last_name"]

    def update_full_presto_data(self, user, info:Namespace):
        """Download copy of Prestodoctor photo files to local server.

        Set user's medical license verified if it looks good.
        """

        user.license_initial_upload_completed_at = now()

        # Trust Prestodoctor licenses if they are not expired
        if info.recommendation.expires > time.time():
            user.license_verified_by = None
            user.license_verified_at = now()
            user.presto_license_number = info.recommendation.id_num
            user.medical_license_upload_completed_at = now()
            user.license_initial_upload_completed_at = now()

        # Download copy of government issued id so the driver can check this is the right person
        driving_license = UserMedia.fetch_from_url(self.registry, info.photo_id.url, user=user)
        driving_license.approved_by = None
        driving_license.approved_at = now()
        driving_license.store_bbb_copy(self.registry, "driving")  # Backwards compatibility

        # Set a marker for tests so we know we don't do this operation twice
        user.user_data["social"]["prestodoctor"]["full_data_updated_at"] = now().isoformat()

    def update_every_login_social_data(self, user, data):
        """Update user data every time they relogin."""

        # If the user has been using our system before, get the current active prestodoctor recommendation issued date
        last_known_recommendation_issued = user.user_data["social"].get("prestodoctor", {}).get("recommendation", {}).get("issued", None)

        super(PrestodoctorMapper, self).update_every_login_social_data(user, data)

        # Convert data to dotted notation for saving wrists below
        # http://stackoverflow.com/a/16279578/315168
        info = Namespace(**data)
        info.address = Namespace(**info.address)
        info.photo_id = Namespace(**info.photo_id)
        info.recommendation = Namespace(**info.recommendation)

        # Map Presto fields to our fields
        mappings = {
            "dob": info.dob,
            "photo_url": info.photo,
            "country": "US",
            "zipcode": info.address.zip5,
            "zip4": info.address.zip4,
            "gender": None,
            "first_name": info.first_name,
            "last_name": info.last_name,
            "full_name": info.first_name + " " + info.last_name,
            "city": info.address.city,
            "state": info.address.state,
            "postal_code": info.address.zip5,
            "address": info.address.address1,
            "apartment": info.address.address2,
            "external_data_updated": now().isoformat()
        }

        # TODO: Set user medical license verified if Presto gives us its number

        # Update internal structure. Only override existing value if we have data from Presto.
        # E.g. phone number might be missing, but we have it, so we don't want to replace existing phone number with empty string.
        for key, value in mappings.items():
            if value:
                user.user_data[key] = value

        if user.user_data["social"]["prestodoctor"]["recommendation"].get("issued") != last_known_recommendation_issued:
            # The prestodoctor evaluation issue has changed, do the heavy data update
            self.update_full_presto_data(user, info)

    def capture_social_media_user(self, request, result):
        """Extract social media information from the Authomatic login result in order to associate the user account."""

        # Should not happen
        assert not result.error

        email = result.user.base_data.get("email")

        if not email:
            # We cannot login if the Facebook doesnt' give us email as we use it for the user mapping
            # This can also happen when you have not configured Facebook app properly in the developers.facebook.com
            raise NotSatisfiedWithData("Email address is needed in order to user this service and we could not get one from your social media provider. Please try to sign up with your email instead.")

        user = self.get_or_create_user_by_social_medial_email(request, result.user)

        return user

#: This map is to satisfy Authomatic module loader
PROVIDER_ID_MAP = [PrestodoctorAuthomatic]