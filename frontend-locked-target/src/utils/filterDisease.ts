// utils/filterUtils.js

/**
 * Filters data based on selected diseases.
 *
 * @param {Array} data - The full processed data array.
 * @param {Array} selectedDiseases - Currently selected diseases.
 * @param {Array} allDiseases - Full list of all possible diseases.
 * @param {string} key - The field name in data to match against disease (default "Disease").
 * @returns {Array} - Filtered data.
 */
export const filterByDiseases = (
    data = [],
    selectedDiseases = [],
    allDiseases = [],
    key = "Disease"
  ) => {
    if (!data.length) return [];
  
    // Return all if all diseases are selected
    if (selectedDiseases.length === allDiseases.length) {
      return data;
    }
  
    return data.filter((row) =>
      selectedDiseases.some(
        (disease) => disease.toLowerCase() === row[key]?.toLowerCase()
      )
    );
  };
  