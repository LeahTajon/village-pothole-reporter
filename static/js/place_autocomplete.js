window.setupPlaceAutocomplete = function ({
    map,
    formId,
    inputId,
    buttonId,
    messageId,
    suggestionsId,
    isAllowed
}) {
    const form = document.getElementById(formId);
    const input = document.getElementById(inputId);
    const button = document.getElementById(buttonId);
    const message = document.getElementById(messageId);
    const suggestions = document.getElementById(suggestionsId);

    if (!form || !input || !button || !message || !suggestions) {
        return;
    }

    let debounceTimer;
    let controller;
    let activeIndex = -1;
    let results = [];

    function closeSuggestions() {
        suggestions.hidden = true;
        suggestions.replaceChildren();
        activeIndex = -1;
        results = [];
    }

    function showMessage(text) {
        message.textContent = text;
    }

    function getPlaceName(properties) {
        return properties.name ||
            properties.street ||
            properties.locality ||
            "Unnamed place";
    }

    function getPlaceDetail(properties) {
        return [
            properties.street && properties.name !== properties.street
                ? properties.street
                : null,
            properties.district,
            properties.city,
            properties.state,
            properties.country
        ].filter(Boolean).filter((value, index, array) =>
            array.indexOf(value) === index
        ).join(", ");
    }

    function updateActiveOption() {
        const options = suggestions.querySelectorAll(
            ".place-suggestion"
        );

        options.forEach((option, index) => {
            const active = index === activeIndex;
            option.classList.toggle("active", active);
            option.setAttribute("aria-selected", String(active));

            if (active) {
                option.scrollIntoView({ block: "nearest" });
            }
        });
    }

    function choosePlace(place) {
        const coordinates = place.geometry.coordinates;
        const longitude = Number(coordinates[0]);
        const latitude = Number(coordinates[1]);

        if (
            !Number.isFinite(latitude) ||
            !Number.isFinite(longitude) ||
            (isAllowed && !isAllowed(latitude, longitude))
        ) {
            showMessage("Please choose a place inside Dededo.");
            return;
        }

        // Move the existing map without creating a marker.
        map.setView([latitude, longitude], 17, {
            animate: true
        });

        input.value = getPlaceName(place.properties);
        showMessage("Map moved to: " + (
            place.properties.name || place.properties.label ||
            getPlaceDetail(place.properties)
        ));

        closeSuggestions();
    }

    function renderSuggestions(places) {
        suggestions.replaceChildren();
        results = places;
        activeIndex = -1;

        places.forEach((place, index) => {
            const properties = place.properties || {};
            const option = document.createElement("button");

            option.type = "button";
            option.className = "place-suggestion";
            option.setAttribute("role", "option");
            option.setAttribute("aria-selected", "false");

            const icon = document.createElement("span");
            icon.className = "place-suggestion-icon";
            icon.innerHTML = '<i class="bi bi-geo-alt"></i>';

            const text = document.createElement("span");
            text.className = "place-suggestion-text";

            const name = document.createElement("span");
            name.className = "place-suggestion-name";
            name.textContent = getPlaceName(properties);

            const detail = document.createElement("span");
            detail.className = "place-suggestion-detail";
            detail.textContent =
                getPlaceDetail(properties) ||
                properties.osm_value ||
                "Location";

            text.append(name, detail);
            option.append(icon, text);

            option.addEventListener("mouseenter", () => {
                activeIndex = index;
                updateActiveOption();
            });

            option.addEventListener("click", () => {
                choosePlace(place);
            });

            suggestions.appendChild(option);
        });

        suggestions.hidden = places.length === 0;
    }

    async function searchPlaces(query) {
        if (controller) {
            controller.abort();
        }

        controller = new AbortController();

        showMessage("Searching for places...");

        try {
            const params = new URLSearchParams({
                q: query,
                limit: "8",
                lang: "en",
                lat: "13.5178",
                lon: "144.8391",
                bbox: "144.76,13.45,144.92,13.59"
            });

            const response = await fetch(
                "https://photon.komoot.io/api/?" + params.toString(),
                {
                    signal: controller.signal,
                    headers: { Accept: "application/json" }
                }
            );

            if (!response.ok) {
                throw new Error("Place search failed.");
            }

            const data = await response.json();

            const places = (data.features || []).filter(place => {
                const coordinates = place.geometry?.coordinates;

                if (!coordinates) return false;

                const longitude = Number(coordinates[0]);
                const latitude = Number(coordinates[1]);

                return (
                    Number.isFinite(latitude) &&
                    Number.isFinite(longitude) &&
                    (!isAllowed || isAllowed(latitude, longitude))
                );
            });

            if (input.value.trim() !== query) return;

            renderSuggestions(places);

            showMessage(
                places.length
                    ? "Choose a matching place below."
                    : "No matching places found in the search area."
            );
        } catch (error) {
            if (error.name === "AbortError") return;

            console.error("Autocomplete error:", error);
            closeSuggestions();
            showMessage("Place search is unavailable. Please try again.");
        }
    }

    input.addEventListener("input", function () {
        clearTimeout(debounceTimer);

        if (controller) controller.abort();

        closeSuggestions();

        const query = input.value.trim();

        if (query.length < 2) {
            showMessage("");
            return;
        }

        debounceTimer = setTimeout(() => {
            searchPlaces(query);
        }, 350);
    });

    input.addEventListener("keydown", function (event) {
        if (suggestions.hidden || !results.length) {
            if (event.key === "Escape") closeSuggestions();
            return;
        }

        if (event.key === "ArrowDown") {
            event.preventDefault();
            activeIndex = (activeIndex + 1) % results.length;
            updateActiveOption();
        } else if (event.key === "ArrowUp") {
            event.preventDefault();
            activeIndex =
                (activeIndex - 1 + results.length) % results.length;
            updateActiveOption();
        } else if (event.key === "Enter" && activeIndex >= 0) {
            event.preventDefault();
            choosePlace(results[activeIndex]);
        } else if (event.key === "Escape") {
            closeSuggestions();
        }
    });

    form.addEventListener("submit", function (event) {
        event.preventDefault();

        if (activeIndex >= 0 && results[activeIndex]) {
            choosePlace(results[activeIndex]);
            return;
        }

        if (results.length === 1) {
            choosePlace(results[0]);
            return;
        }

        if (results.length > 1) {
            showMessage("Please select a place from the suggestions.");
            return;
        }

        const query = input.value.trim();

        if (query.length >= 2) {
            searchPlaces(query);
        } else {
            showMessage("Enter at least two characters to search.");
        }
    });

    document.addEventListener("click", function (event) {
        if (!form.contains(event.target)) {
            closeSuggestions();
        }
    });
};