export type Citation = {
    title: string;
    authors: string[];
    date: string;
    url: string;
}

export type Followup = {
    text: string;
    pageid: string;
    score: number;
}

export type Entry = UserEntry | AssistantEntry | ErrorMessage | StampyMessage;

export type UserEntry = {
    role: "user";
    content: string;
}

export type AssistantEntry = {
    role: "assistant";
    content: string;
    citations: Citation[];
    base_count: number; // the number to start counting citations at
}

export type ErrorMessage = {
    role: "error";
    content: string;
}

export type StampyMessage = {
    role: "stampy";
    content: string;
    url: string;
}
