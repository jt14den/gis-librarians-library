#!/usr/bin/env Rscript
# data-prep.R
# Run this script once to produce output/institutions_analysis.csv
# Requires: tidyverse, tidygeocoder
# install.packages(c("tidyverse", "tidygeocoder"))

library(tidyverse)

if (!requireNamespace("tidygeocoder", quietly = TRUE)) {
  install.packages("tidygeocoder", repos = "https://cloud.r-project.org")
}
library(tidygeocoder)

# ── 1. Load source data ────────────────────────────────────────────────────────

carnegie <- read_csv("data/raw/carnegie_r1_2025.csv", show_col_types = FALSE)
verified <- read_csv("output/verified.csv", show_col_types = FALSE)
no_gis   <- read_csv("output/no_gis_librarian.csv", show_col_types = FALSE)
arl      <- read_csv("data/reference/arl_members.csv", show_col_types = FALSE)

# ── 2. Build institution-level GIS status ─────────────────────────────────────

inst_with_gis <- verified %>%
  count(Institution, name = "team_size") %>%
  mutate(has_gis = TRUE)

inst_no_gis <- no_gis %>%
  select(Institution) %>%
  mutate(has_gis = FALSE, team_size = 0L)

gis_status <- bind_rows(inst_with_gis, inst_no_gis)

# ── 3. Simplify Carnegie classifications ──────────────────────────────────────

carnegie_clean <- carnegie %>%
  rename(Institution = name) %>%
  mutate(
    # Simplified size label
    size = factor(Size, levels = c("Small", "Medium", "Large", "Very Large")),
    # Public vs private
    sector = case_when(
      str_detect(control, "Public") ~ "Public",
      TRUE ~ "Private"
    ),
    # Simplified institutional type
    inst_type = case_when(
      str_detect(`Institutional Classification`, "Special Focus") ~ "Special Focus",
      str_detect(`Institutional Classification`, "Large") ~ "Large Research",
      str_detect(`Institutional Classification`, "Medium") ~ "Medium Research",
      TRUE ~ "Other"
    ),
    # Graduate program mix (simplified)
    grad_mix = case_when(
      str_detect(`Graduate Academic Program Mix`, "STEM") ~ "STEM-focused",
      str_detect(`Graduate Academic Program Mix`, "Professions") ~ "Professions-focused",
      str_detect(`Graduate Academic Program Mix`, "Balanced") ~ "Balanced",
      str_detect(`Graduate Academic Program Mix`, "Special") ~ "Special Focus",
      TRUE ~ "Other"
    )
  ) %>%
  select(Institution, city, state, sector, size, inst_type, grad_mix,
         `Institutional Classification`, `Graduate Academic Program Mix`,
         `Research Activity Designation`)

# ── 4. ARL membership flag ────────────────────────────────────────────────────

# Fuzzy-ish join: flag institutions whose name appears in ARL list
arl_names <- arl %>% pull(1) %>% str_to_lower()

carnegie_clean <- carnegie_clean %>%
  mutate(is_arl = str_to_lower(Institution) %in% arl_names)

# ── 5. UC system flag ─────────────────────────────────────────────────────────

uc_campuses <- c(
  "University of California-Berkeley",
  "University of California-Davis",
  "University of California-Irvine",
  "University of California-Los Angeles",
  "University of California-Merced",
  "University of California-Riverside",
  "University of California-San Diego",
  "University of California-San Francisco",
  "University of California-Santa Barbara",
  "University of California-Santa Cruz"
)

carnegie_clean <- carnegie_clean %>%
  mutate(is_uc = Institution %in% uc_campuses)

# ── 6. Combine ────────────────────────────────────────────────────────────────

combined <- carnegie_clean %>%
  left_join(gis_status, by = "Institution") %>%
  mutate(
    has_gis  = replace_na(has_gis, FALSE),
    team_size = replace_na(team_size, 0L),
    team_size_cat = case_when(
      team_size == 0 ~ "None",
      team_size == 1 ~ "1",
      team_size == 2 ~ "2",
      team_size >= 3 ~ "3+"
    ) %>% factor(levels = c("None", "1", "2", "3+"))
  )

# ── 7. Geocode ────────────────────────────────────────────────────────────────
# Uses OSM (free). Coordinates cached in output/geocode_cache.csv.
# Only geocodes rows missing from the cache (new institutions or first run).

geocode_cache_path <- "output/geocode_cache.csv"

if (file.exists(geocode_cache_path)) {
  coord_cache <- read_csv(geocode_cache_path, show_col_types = FALSE,
                           col_types = cols(Institution = col_character(),
                                            lat = col_double(),
                                            lon = col_double()))
} else {
  coord_cache <- tibble(Institution = character(), lat = numeric(), lon = numeric())
}

combined <- combined %>%
  left_join(coord_cache, by = "Institution")

needs_geocoding <- combined %>% filter(is.na(lat) | is.na(lon))

if (nrow(needs_geocoding) > 0) {
  message(sprintf("Geocoding %d institutions (new or missing coordinates)...",
                  nrow(needs_geocoding)))
  newly_geocoded <- needs_geocoding %>%
    select(-any_of(c("lat", "lon"))) %>%
    geocode(
      city   = city,
      state  = state,
      method = "osm",
      lat    = lat,
      long   = lon
    )
  # Update cache
  updated_cache <- bind_rows(
    coord_cache,
    newly_geocoded %>% select(Institution, lat, lon) %>% filter(!is.na(lat))
  ) %>% distinct(Institution, .keep_all = TRUE)
  write_csv(updated_cache, geocode_cache_path)

  combined <- bind_rows(
    combined %>% filter(!is.na(lat), !is.na(lon)),
    newly_geocoded
  )
} else {
  message("All coordinates cached — skipping geocoding.")
}

geocoded <- combined

# ── 8. Add HERD R&D rankings ──────────────────────────────────────────────────

herd <- read_csv("data/reference/carnegie_herd_join.csv", show_col_types = FALSE) %>%
  select(Institution, herd_rank_2024, herd_pct_2024, herd_rd_2024_000) %>%
  mutate(
    herd_rd_billions = herd_rd_2024_000 / 1e6,  # convert $000s to billions
    herd_rank_2024   = as.integer(herd_rank_2024)
  )

geocoded <- geocoded %>%
  left_join(herd, by = "Institution")

# ── 9. Write output ───────────────────────────────────────────────────────────

write_csv(geocoded, "output/institutions_analysis.csv")
message("Wrote output/institutions_analysis.csv")
