"use client";

import { MarkdownText } from "@/components/assistant-ui/markdown-text";
import { Button } from "@/components/ui/button";
import {
  ComposerPrimitive,
  MessagePrimitive,
  ThreadPrimitive,
} from "@assistant-ui/react";
import { ArrowUpIcon, SquareIcon } from "lucide-react";
import type { FC } from "react";

export const Thread: FC = () => {
  return (
    <ThreadPrimitive.Root
      className="aui-root aui-thread-root flex h-full flex-col bg-background"
      style={{
        ["--thread-max-width" as string]: "44rem",
      }}
    >
      <ThreadPrimitive.Viewport className="aui-thread-viewport relative flex flex-1 flex-col overflow-y-scroll scroll-smooth px-4 pt-8">
        <ThreadPrimitive.Empty>
          <ThreadWelcome />
        </ThreadPrimitive.Empty>

        <ThreadPrimitive.Messages
          components={{
            UserMessage,
            AssistantMessage,
          }}
        />

        <ThreadPrimitive.ViewportFooter className="sticky bottom-0 mx-auto mt-auto flex w-full max-w-[var(--thread-max-width)] flex-col gap-4 rounded-t-3xl bg-background pb-4 md:pb-6">
          <Composer />
        </ThreadPrimitive.ViewportFooter>
      </ThreadPrimitive.Viewport>
    </ThreadPrimitive.Root>
  );
};

const ThreadWelcome: FC = () => {
  return (
    <div className="mx-auto my-auto flex w-full max-w-[var(--thread-max-width)] grow flex-col items-center justify-center">
      <div className="flex flex-col items-center gap-4 px-4 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary">
          <span className="text-2xl font-bold text-primary-foreground">AI</span>
        </div>
        <h1 className="text-2xl font-semibold text-foreground">
          DHG AI Factory
        </h1>
        <p className="text-lg text-muted-foreground">
          Select a graph and send a message to get started.
        </p>
      </div>
    </div>
  );
};

const Composer: FC = () => {
  return (
    <ComposerPrimitive.Root className="relative flex w-full flex-col rounded-2xl border border-input bg-background px-1 pt-2 shadow-sm transition-shadow focus-within:border-ring focus-within:ring-2 focus-within:ring-ring/20">
      <ComposerPrimitive.Input
        placeholder="Send a message..."
        className="mb-1 max-h-32 min-h-14 w-full resize-none bg-transparent px-4 pt-2 pb-3 text-sm outline-none placeholder:text-muted-foreground"
        rows={1}
        autoFocus
        aria-label="Message input"
      />
      <div className="relative mx-2 mb-2 flex items-center justify-end">
        <ComposerPrimitive.Send asChild>
          <Button
            type="button"
            variant="default"
            size="icon"
            className="size-8 rounded-full"
            aria-label="Send message"
          >
            <ArrowUpIcon className="size-4" />
          </Button>
        </ComposerPrimitive.Send>
      </div>
    </ComposerPrimitive.Root>
  );
};

const AssistantMessage: FC = () => {
  return (
    <MessagePrimitive.Root
      className="relative mx-auto w-full max-w-[var(--thread-max-width)] py-3"
      data-role="assistant"
    >
      <div className="wrap-break-word px-2 text-foreground leading-relaxed">
        <MessagePrimitive.Content
          components={{
            Text: MarkdownText,
          }}
        />
      </div>
    </MessagePrimitive.Root>
  );
};

const UserMessage: FC = () => {
  return (
    <MessagePrimitive.Root
      className="mx-auto flex w-full max-w-[var(--thread-max-width)] justify-end py-3"
      data-role="user"
    >
      <div className="max-w-[85%] rounded-2xl bg-muted px-4 py-2.5 text-foreground">
        <MessagePrimitive.Content />
      </div>
    </MessagePrimitive.Root>
  );
};
