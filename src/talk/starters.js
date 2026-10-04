/** Three questions to start with for each place, as message keys; Plans has its own. */
const STARTERS = {
  today: ["avaStartNext", "avaStartDay", "avaStartPlanToday"],
  plans: ["avaStartPlansDiffer", "avaStartPlanToday", "avaStartWhyChosen"],
  calendar: ["avaStartWeek", "avaStartUnfinished", "avaStartRoom"],
  records: ["avaStartGoalAttention", "avaStartGoalNext", "avaStartGoalProgress"],
  library: ["avaStartNotesToday", "avaStartStudyNext", "avaStartNotesGoals"],
};

/**
 * The questions Ava suggests for what is on show, so a conversation never starts from an empty box.
 * @param {string} topic - `today`, `plans`, `calendar`, `records` or `library`.
 * @returns {string[]} The questions' message keys; Today's for a place without its own.
 */
export function starterPrompts(topic) {
  return STARTERS[topic] || STARTERS.today;
}
