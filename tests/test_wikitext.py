"""Tests for the shared wikitext renderer."""

from scrapers.wikitext import render_image, render_item_data, render_text, slugify


class TestValueTemplates:
    def test_cash_template(self):
        assert render_text("{{$|50,000}}") == "$50,000"

    def test_meteor_shards_template(self):
        assert render_text("{{Meteor Shards|30}}") == "30 Meteor Shards"

    def test_exp_template(self):
        assert render_text("{{EXP|10,000}}") == "10,000 EXP"

    def test_other_value_units(self):
        assert render_text("{{Sand Dollars|1000}}") == "1000 Sand Dollars"
        assert render_text("{{Eggs|3}}") == "3 Eggs"
        assert render_text("{{Candy|60}}") == "60 Candy"
        assert render_text("{{Heart Crystals|2}}") == "2 Heart Crystals"

    def test_stat_template(self):
        assert render_text("{{Stat|Luck}}") == "Luck"
        assert render_text("{{stat|Dig Strength}}") == "Dig Strength"

    def test_rarity_templates(self):
        assert render_text("{{common}}") == "Common"
        assert render_text("{{rare}}") == "Rare"
        assert render_text("{{Legendary}}") == "Legendary"
        assert render_text("{{mythical}}") == "Mythical"

    def test_unknown_template_without_arguments_uses_its_name(self):
        assert render_text("{{Rubble Creek}}") == "Rubble Creek"
        assert render_text("{{Astral Caverns}}") == "Astral Caverns"
        assert render_text("{{The Void}}") == "The Void"

    def test_unknown_template_with_arguments_uses_them(self):
        assert render_text("{{Fortune River|Fortune River Town}}") == "Fortune River Town"

    def test_named_parameters_are_not_leaked(self):
        assert "bar" not in render_text("{{foo|bar=baz}}")
        assert "baz" not in render_text("{{foo|bar=baz}}")

    def test_underscored_template_name_becomes_spaces(self):
        assert render_text("{{A_B_C}}") == "A B C"


class TestLinks:
    def test_plain_wikilink(self):
        assert render_text("[[Gold]]") == "Gold"

    def test_wikilink_with_label(self):
        assert render_text("[[Events#tabber-River_Rapids|River Rapids]]") == "River Rapids"

    def test_wikilink_target_underscores_become_spaces(self):
        assert render_text("[[Prospector's Shop]]") == "Prospector's Shop"

    def test_external_link_keeps_its_label(self):
        assert render_text("[https://example.com label here]") == "label here"


class TestHtmlAndEntities:
    def test_entities_become_characters(self):
        assert render_text("2&times; boost") == "2× boost"

    def test_non_breaking_space_becomes_a_space(self):
        assert render_text("3&nbsp;Gold") == "3 Gold"

    def test_ampersand_entity(self):
        assert render_text("a&amp;b") == "a&b"

    def test_line_breaks_become_newlines(self):
        assert render_text("first<br />second") == "first\nsecond"

    def test_superscript_keeps_its_content(self):
        assert render_text("3&nbsp;[[Gold]]<sup>&nbsp;c</sup>") == "3 Gold (c)"

    def test_superscript_in_a_recipe(self):
        rendered = render_text("1&nbsp;[[Celestium]]<sup>&nbsp;c</sup><br />5&nbsp;[[Gold]]")
        assert rendered == "1 Celestium (c)\n5 Gold"

    def test_percent_encoding_is_decoded(self):
        assert render_text("Blueprint_%26_Trinket_Vendor") == "Blueprint_&_Trinket_Vendor"


class TestArtifacts:
    def test_leading_pipe_is_removed(self):
        assert render_text("| some text") == "some text"

    def test_table_row_markers_are_removed(self):
        assert render_text("|-\n| Panel line: value") == "Panel line: value"

    def test_cell_style_attribute_is_removed(self):
        rendered = render_text('|-\n| style="padding:3px 16px;" | Panel line: Dig Strength')
        assert rendered == "Panel line: Dig Strength"

    def test_trailing_equals_quote_is_removed(self):
        assert render_text('A relic that does a thing.\n\n="') == "A relic that does a thing."

    def test_bold_and_italic_markers_are_removed(self):
        assert render_text("'''Rain Stone''' is a relic") == "Rain Stone is a relic"

    def test_blank_lines_are_dropped(self):
        assert render_text("first\n\n\nsecond") == "first\nsecond"

    def test_whitespace_is_collapsed(self):
        assert render_text("too    many   spaces") == "too many spaces"

    def test_empty_string(self):
        assert render_text("") == ""


class TestRenderImage:
    def test_plain_file_name(self):
        assert render_image("Abyssal Rune.png") == "Abyssal Rune.png"

    def test_file_with_options(self):
        assert render_image("Accretion DiskBP.png|100px|frameless|right") == "Accretion DiskBP.png"

    def test_thumb_with_caption(self):
        assert render_image("Rain Stone.png|thumb|The '''Rain Stone'''") == "Rain Stone.png"

    def test_file_prefix_is_removed(self):
        assert render_image("File:Modifier Perfect.png") == "Modifier Perfect.png"

    def test_empty(self):
        assert render_image("") == ""


class TestRenderItemData:
    def test_nested_values_are_rendered(self):
        data = {
            "description": "A [[Golden]] pan",
            "stats": {"luck": "{{Stat|Luck}}"},
            "steps": ["Buy a {{$|100}} pan"],
        }
        rendered = render_item_data(data)
        assert rendered["description"] == "A Golden pan"
        assert rendered["stats"]["luck"] == "Luck"
        assert rendered["steps"] == ["Buy a $100 pan"]

    def test_machine_values_are_preserved(self):
        data = {
            "color": "#00ffe1",
            "item_slug": "relic-luck-booster",
            "image_url": "https://example.com/a.png",
            "wiki_id": "12",
        }
        assert render_item_data(data) == data

    def test_numbers_are_preserved(self):
        data = {"value": 23000.0, "luck": 1.25, "requires_geothermal": False}
        assert render_item_data(data) == data

    def test_image_keys_are_reduced_to_file_names(self):
        data = {"image": "Abyssal Rune.png|50px", "icon": "inh I.PNG|50px"}
        rendered = render_item_data(data)
        assert rendered["image"] == "Abyssal Rune.png"
        assert rendered["icon"] == "inh I.PNG"

    def test_non_dict_input(self):
        assert render_item_data(None) is None


class TestSlugify:
    def test_basic(self):
        assert slugify("Rusty Pan") == "rusty-pan"

    def test_apostrophes_and_parentheses_are_dropped(self):
        assert slugify("Traveler's Mix (Small)") == "travelers-mix-small"
